from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from src.adapters.context_builder_adapter import ContextBuilderAdapter
from src.adapters.question_builder_adapter import QuestionBuilderAdapter
from src.adapters.retriever_adapter import RetrieverAdapter
from src.adapters.personality_builder_adapter import PersonalityBuilderAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.core.timeouts import TimeoutTools
from src.core.utils import EnvTools
from src.pydantic_schemas.agent_controller import (
    ComponentHealth,
    GraphState,
    HealthCheck,
    InferenceParams,
    Personalities,
    QuestionResponse,
    ServiceStatus,
    UserQuery,
)

from src.agents_graphs.graph_builder import GraphBuilder

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class LLMGraphOrchestrator:
    def __init__(self) -> None:
        self.vllm_adapter = VLLMAdapter()
        self.retriever_adapter = RetrieverAdapter()
        self.question_builder_adapter = QuestionBuilderAdapter()
        self.context_builder_adapter = ContextBuilderAdapter()
        self.personality_builder_adapter = PersonalityBuilderAdapter()
        self.default_collection = EnvTools.required_load_env_var('DEFAULT_RETRIEVER_COLLECTION')
        max_len_env = float(EnvTools.required_load_env_var('VLLM_TALKING_MAX_LEN'))
        self.max_context_chars = int(max_len_env / 2)
        self.min_results_required = int(EnvTools.required_load_env_var('VLLM_TALKING_MIN_RESULTS'))
        self.checkpointer = MemorySaver()
        self.health_timeout_sec = TimeoutTools.get_health_check_timeout()
        
        # Initialize inference defaults
        self.inference_defaults = InferenceParams(
            model_name=EnvTools.load_env_var("VLLM_MODEL_NAME") or "vllm",
            temperature=float(EnvTools.load_env_var("LLM_TEMP") or "0.2"),
            max_tokens=int(EnvTools.load_env_var("LLM_MAX_TOKENS") or "800"),
        )

        self.graph_builder = GraphBuilder(
            self.vllm_adapter,
            self.retriever_adapter,
            self.question_builder_adapter,
            self.context_builder_adapter,
            self.personality_builder_adapter,
        )

        self.agents_graphs: dict[str, Any] = {}


    async def answer_question(
        self,
        query: UserQuery,
        run_id: str | None = None,
    ) -> QuestionResponse:
        try:
            # user provided agent name in it's query.
            # we using graph of specific agent here.
            graph = self.agents_graphs.get(query.agent_name)

            if graph is None:
                graph = self.graph_builder.build_graph(
                    query.agent_name,
                    self.checkpointer
                )

                self.agents_graphs[query.agent_name] = graph

        except ValueError as exc:
            return QuestionResponse(
                answer='',
                success=False,
                error=str(exc)
            )

        initial: GraphState = {
            'question_id': str(uuid.uuid4()),
            'started_at_ms': time.time() * 1000,
            'timings_ms': {},
            'collection_name': self.default_collection,
            'max_context_chars': self.max_context_chars,
            'min_results_required': self.min_results_required,
            'query': query,
            'agent_name': query.agent_name,
            'success': False,
            'context_digests': [],
            'personalities': Personalities(personalities={}),
            'inference_params': self.inference_defaults,
        }

        state: GraphState = await graph.ainvoke(
            initial,
            config={'configurable': {'thread_id': run_id or initial['question_id']}}
        )

        return QuestionResponse(
            answer=state.get('response_answer', ''),
            success=state.get('success', False),
            error=state.get('error', ''),
        )


    async def health_check(self) -> HealthCheck:
        async def run_check(
            name: str,
            check_callable: Callable[[], Awaitable[object]],
        ) -> ComponentHealth:
            try:
                result = await asyncio.wait_for(
                    check_callable(),
                    timeout=self.health_timeout_sec,
                )

            except TimeoutError:
                details = f'timeout after {self.health_timeout_sec:.1f}s'
                return ComponentHealth(name=name, status=ServiceStatus.UNHEALTHY, details=details)
                
            except Exception as exc:  # noqa: BLE001
                logger.error(f'Health check for {name} failed: {exc}')
                return ComponentHealth(name=name, status=ServiceStatus.UNHEALTHY, details=str(exc))

            is_healthy = False
            detail_text: str | None = None

            if isinstance(result, bool):
                is_healthy = result
                if not result:
                    detail_text = 'reported unhealthy'

            else:
                status_value = getattr(result, 'status', '')
                success_value = getattr(result, 'success', None)

                if isinstance(success_value, bool):
                    is_healthy = success_value
                    
                elif isinstance(status_value, str):
                    is_healthy = status_value.lower() == 'healthy'

                else:
                    is_healthy = bool(result)

                detail_parts: list[str] = []
                result_details = getattr(result, 'details', '')
                if result_details:
                    detail_parts.append(str(result_details))

                hybrid_embedder_status = getattr(result, 'hybrid_embedder_status', '')
                if hybrid_embedder_status and str(hybrid_embedder_status).lower() != 'healthy':
                    detail_parts.append(f'hybrid_embedder:{hybrid_embedder_status}')

                qdrant_status = getattr(result, 'qdrant_status', '')
                if qdrant_status and str(qdrant_status).lower() != 'healthy':
                    detail_parts.append(f'qdrant:{qdrant_status}')

                if detail_parts:
                    detail_text = ', '.join(detail_parts)

            if is_healthy:
                return ComponentHealth(
                    name=name,
                    status=ServiceStatus.HEALTHY,
                    details=None
                )

            return ComponentHealth(
                name=name,
                status=ServiceStatus.UNHEALTHY,
                details=detail_text or 'reported unhealthy',
            )

        components = await asyncio.gather(
            run_check('vllm_talking', self.vllm_adapter.health_check),
            run_check('question_builder', self.question_builder_adapter.health_check),
            run_check('retriever', self.retriever_adapter.health_check),
            run_check('context_builder', self.context_builder_adapter.health_check),
            run_check('personality_builder', self.personality_builder_adapter.health_check),
        )

        overall_status = ServiceStatus.HEALTHY if all(
            component.status == ServiceStatus.HEALTHY for component in components
        ) else ServiceStatus.UNHEALTHY

        return HealthCheck(
            overall_status=overall_status,
            components=list(components),
        )


