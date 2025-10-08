from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.logging import PersonalityBuilderLogger
from src.pydantic_schemas.agent_controller import GraphState, PersonalityResponse, Personality, Personalities
from src.agents_graphs.graph_tools import GraphTools
from src.core.handlers import ResponseHandler
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.adapters.personality_builder_adapter import PersonalityBuilderAdapter


class PersonalityBuilderNode(BaseNode):
    def __init__(self, adapter: PersonalityBuilderAdapter) -> None:
        super().__init__('PERSONALITY_NODE_TIMEOUT_SEC', 15.0, 3)
        self.adapter = adapter


    _PERSONALITIES: tuple[str, ...] = (
        'responder', 
        'summarizer',
        'planner',
        'evidencer', 
        'gatekeeper',
        'response_planner',
        'response_critic'
    )


    def _get_node_name(self) -> str:
        return 'build_personalities'


    async def _execute_impl(
        self,
        graph_state: GraphState
    ) -> GraphState:
        # here we just pulling every personality from personality builder.
        # it's returns list of JSON schemas.
        # we store JSON schemas in graph state and than compile
        # pydantic schemas from JSON schemas for pydantic_ai working.

        response: PersonalityResponse = await self.adapter.build_personalities(
            list(self._PERSONALITIES),
            graph_state.get('agent_name', '')
        )

        if not response.success:
            return ResponseHandler.handle_failure(
                graph_state,
                f"Personality building failed: {response.error or 'unknown'}"
            )

        def _prepare_schema(
            schema_like: Any,
            name: str
        ) -> dict[str, Any] | None:
            if not schema_like:
                return None
            
            data = schema_like.model_dump() if hasattr(schema_like, "model_dump") else schema_like
            if not isinstance(data, dict):
                return None
            
            return data

        personalities = Personalities(
            personalities={
                personality.name: Personality(
                    name=personality.name,
                    system_prompt=personality.system_prompt,
                    response_schema=_prepare_schema(getattr(personality, "response_schema", None), personality.name)
                )
                for personality in response.personalities
            }
        )

        return ResponseHandler.handle_success(
            graph_state,
            'success',
            additional_data={'personalities': personalities}
        )



    def _log_success(
        self,
        graph_state: GraphState,
        elapsed_ms: float
    ) -> None:
        PersonalityBuilderLogger.log_personality_building(
            question_id=graph_state['question_id'],
            personalities=graph_state['personalities'],
            building_time_ms=elapsed_ms,
            success=True,
        )

        
