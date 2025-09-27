
from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from loguru import logger
from langgraph.checkpoint.memory import MemorySaver

from src.adapters.context_builder_adapter import ContextBuilderAdapter
from src.adapters.question_builder_adapter import QuestionBuilderAdapter
from src.adapters.retriever_adapter import RetrieverAdapter
from src.adapters.system_prompt_builder_adapter import SystemPromptBuilderAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.core.timeouts import TimeoutTools
from src.core.utils import EnvTools
from src.domain.models import ComponentHealth, HealthCheck, QuestionResponse, ServiceStatus, UserQuery
from src.graph.graph_builder import GraphBuilder

if TYPE_CHECKING:
    from src.domain.models import GraphState


class LLMGraphOrchestrator:
    def __init__(self) -> None:
        self.vllm_adapter = VLLMAdapter()
        self.retriever_adapter = RetrieverAdapter()
        self.question_builder_adapter = QuestionBuilderAdapter()
        self.context_builder_adapter = ContextBuilderAdapter()
        self.system_prompt_builder_adapter = SystemPromptBuilderAdapter()
        self.default_collection = EnvTools.required_load_env_var('DEFAULT_RETRIEVER_COLLECTION')
        self.max_context_chars = int(float(EnvTools.required_load_env_var('VLLM_TALKING_MAX_LEN')) / 2)
        self.min_results_required = int(EnvTools.required_load_env_var('VLLM_TALKING_MIN_RESULTS'))
        self.checkpointer = MemorySaver()
        self.health_timeout_sec = TimeoutTools.get_health_check_timeout()

        self.graph_builder = GraphBuilder(
            self.vllm_adapter,
            self.retriever_adapter,
            self.question_builder_adapter,
            self.context_builder_adapter,
            self.system_prompt_builder_adapter,
        )

        self.graph = self.graph_builder.build_graph(self.checkpointer)


    async def answer_question(
        self,
        query: UserQuery,
        run_id: Optional[str] = None,
    ) -> QuestionResponse:
        initial: 'GraphState' = {
            'question_id': str(uuid.uuid4()),
            'started_at_ms': time.time() * 1000,
            'timings_ms': {},
            'collection_name': self.default_collection,
            'max_context_chars': self.max_context_chars,
            'min_results_required': self.min_results_required,
            'query': query,
            'success': False,
        }

        state: 'GraphState' = await self.graph.ainvoke(
            initial,
            config={'configurable': {'thread_id': run_id or initial['question_id']}}
        )

        return QuestionResponse(
            answer=state.get('llm_answer', ''),
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

            except asyncio.TimeoutError:
                details = f'timeout after {self.health_timeout_sec:.1f}s'
                return ComponentHealth(name=name, status=ServiceStatus.UNHEALTHY, details=details)
                
            except Exception as exc:  # noqa: BLE001
                logger.error(f'Health check for {name} failed: {exc}')
                return ComponentHealth(name=name, status=ServiceStatus.UNHEALTHY, details=str(exc))

            is_healthy = False
            detail_text: Optional[str] = None

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

                embedder_status = getattr(result, 'embedder_status', '')
                if embedder_status and str(embedder_status).lower() != 'healthy':
                    detail_parts.append(f'embedder:{embedder_status}')

                qdrant_status = getattr(result, 'qdrant_status', '')
                if qdrant_status and str(qdrant_status).lower() != 'healthy':
                    detail_parts.append(f'qdrant:{qdrant_status}')

                if detail_parts:
                    detail_text = ', '.join(detail_parts)

            if is_healthy:
                return ComponentHealth(name=name, status=ServiceStatus.HEALTHY, details=None)

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
            run_check('system_prompt_builder', self.system_prompt_builder_adapter.health_check),
        )

        overall_status = ServiceStatus.HEALTHY if all(
            component.status == ServiceStatus.HEALTHY for component in components
        ) else ServiceStatus.UNHEALTHY

        return HealthCheck(
            overall_status=overall_status,
            components=list(components),
        )
