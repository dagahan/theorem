from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any

from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from src.adapters.personality_builder_adapter import PersonalityBuilderAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.mcp_adapter import MCPAdapter
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
)

from src.agents_graphs.graph_builder import GraphBuilder

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class LLMGraphOrchestrator:
    def __init__(self) -> None:
        self.vllm_adapter = VLLMAdapter()
        self.personality_builder_adapter = PersonalityBuilderAdapter()
        self.mcp_adapter = MCPAdapter()
        self.default_collection = EnvTools.required_load_env_var('DEFAULT_RETRIEVER_COLLECTION')
        max_len_env = float(EnvTools.required_load_env_var('VLLM_TALKING_MAX_LEN'))
        self.max_context_chars = int(max_len_env / 2)
        self.min_results_required = int(EnvTools.required_load_env_var('VLLM_TALKING_MIN_RESULTS'))
        self.checkpointer = MemorySaver()
        self.health_timeout_sec = TimeoutTools.get_health_check_timeout()
        
        # Initialize inference defaults
        self.inference_defaults = InferenceParams(
            model_name="vllm",
            temperature=float(0.2),
            max_tokens=800,
        )

        self.graph_builder = GraphBuilder(
            self.vllm_adapter,
            self.personality_builder_adapter,
            self.mcp_adapter,
        )

        self.agents_graphs: dict[str, Any] = {}


    async def answer_question(
        self,
        question: str,
        agent_name: str,
        stream: bool = False,
        run_id: str | None = None,
    ) -> QuestionResponse:
        try:
            # user provided agent name in it's query.
            # we using graph of specific agent here.
            graph = self.agents_graphs.get(agent_name)

            if graph is None:
                graph = self.graph_builder.build_graph(
                    agent_name,
                    self.checkpointer
                )

                self.agents_graphs[agent_name] = graph

        except ValueError as exc:
            return QuestionResponse(
                answer='',
                success=False,
                error=str(exc)
            )

        initial_graph_state: GraphState = {
            'question_id': str(uuid.uuid4()),
            'started_at_ms': time.time() * 1000,
            'timings_ms': {},
            'agent_name': agent_name,
            'question': question,
            'context_digests': [],
            'personalities': Personalities(personalities={}),
            'mcp_server': {},
            'mcp_rag_error': '',
            'cot': {},
            'budgets': {},
            'evidence': {},
            'cycle_summary': {},
            'previous_plans': [],
            'plan': {},
            'gate_report': {},
            'gate_decision': '',
            'response_plan': {},
            'plan_ok': False,
            'response_plan_review': {},
            'inference_params': self.inference_defaults,
            'response_answer': '',
            'response_success': False,
            'response_error': '',
            'success': False,
            'error': '',
        }

        state: GraphState = await graph.ainvoke(
            initial_graph_state,
            config={'configurable': {'thread_id': run_id or initial_graph_state['question_id']}}
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
            run_check('personality_builder', self.personality_builder_adapter.health_check),
            run_check('mcp_server', self.mcp_adapter.health_check),
        )

        overall_status = ServiceStatus.HEALTHY if all(
            component.status == ServiceStatus.HEALTHY for component in components
        ) else ServiceStatus.UNHEALTHY

        return HealthCheck(
            overall_status=overall_status,
            components=list(components),
        )


