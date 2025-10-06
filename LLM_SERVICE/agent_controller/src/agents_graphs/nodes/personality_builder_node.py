from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.core.logging import PersonalityBuilderLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.agents_graphs.graph_tools import GraphTools
from src.core.json_schema_to_pydantic import JsonPydanticSchemaCompiler
from src.pydantic_schemas.agent_controller import GraphState, PersonalityResponse, Personality, Personalities

if TYPE_CHECKING:
    from src.adapters.personality_builder_adapter import PersonalityBuilderAdapter


class PersonalityBuilderNode:
    def __init__(self, adapter: PersonalityBuilderAdapter) -> None:
        self.adapter = adapter
        self.schema_compiler = JsonPydanticSchemaCompiler()


    _TIMEOUT_SEC = TimeoutTools.get_timeout('PERSONALITY_NODE_TIMEOUT_SEC', 15.0)
    _PERSONALITIES: tuple[str, ...] = ('Responder', 'Summarizer')


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: GraphState
    ) -> GraphState:
        started_at = time.time()

        try:
            response: PersonalityResponse = await self.adapter.build_personalities(
                list(self._PERSONALITIES),
                graph_state.get('agent_name', '')
            )

        except Exception as ex:  # noqa: BLE001
            return GraphTools.mark_failure(graph_state, f'Personality builder call failed: {ex}')

        if not response.success:
            return GraphTools.mark_failure(
                graph_state,
                f"Personality building failed: {response.error or 'unknown'}",
            )

        def _compile(schema_like: Any, name: str) -> Any:
            if not schema_like:
                return None
            data = schema_like.model_dump() if hasattr(schema_like, "model_dump") else schema_like
            return self.schema_compiler.compile(data, default_name=f"{name}Response")

        personalities = Personalities(
            personalities={
                personality.name: Personality(
                    name=personality.name,
                    system_prompt=personality.system_prompt,
                    response_schema=_compile(getattr(personality, "response_schema", None), personality.name)
                )
                for personality in response.personalities
            }
        )

        graph_state['personalities'] = personalities
        elapsed_ms = GraphTools.record_timing(graph_state, 'build_personalities', started_at)
        
        PersonalityBuilderLogger.log_personality_building(
            question_id=graph_state['question_id'],
            personalities=personalities,
            building_time_ms=elapsed_ms,
            success=True,
        )

        logger.info(
            f"Personalities built: {len(response.personalities)} personas in {elapsed_ms:.2f}ms"
        )

        graph_state['success'] = True

        return graph_state

        
