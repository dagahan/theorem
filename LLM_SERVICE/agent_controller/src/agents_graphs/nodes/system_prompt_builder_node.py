from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from loguru import logger

from src.core.logging import SystemPromptBuilderLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.agents_graphs.graph_tools import GraphTools

if TYPE_CHECKING:
    from src.adapters.system_prompt_builder_adapter import SystemPromptBuilderAdapter
    from src.domain.models import GraphState, SystemPromptResponse


class SystemPromptBuilderNode:
    def __init__(self, adapter: SystemPromptBuilderAdapter) -> None:
        self.adapter = adapter

    _TIMEOUT_SEC = TimeoutTools.get_timeout('SYSTEM_PROMPT_NODE_TIMEOUT_SEC', 15.0)
    _PERSONALITIES: tuple[str, ...] = ('Responder', 'Summarizer')

    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: GraphState
    ) -> GraphState:
        started_at = time.time()

        persona_names = list(self._PERSONALITIES)

        try:
            response: SystemPromptResponse = await self.adapter.build_system_prompt(persona_names)
            
        except Exception as ex:  # noqa: BLE001
            return GraphTools.mark_failure(graph_state, f'System prompt builder call failed: {ex}')

        if not response.success:
            return GraphTools.mark_failure(
                graph_state,
                f"System prompt building failed: {response.error or 'unknown'}",
            )

        graph_state['personality_prompts'] = response.personalities
        graph_state['system_prompt'] = response.personalities.get('Responder', '')

        elapsed_ms = GraphTools.record_timing(graph_state, 'build_system_prompt', started_at)
        responder_prompt = response.personalities.get('Responder', '')

        SystemPromptBuilderLogger.log_system_prompt_building(
            question_id=graph_state['question_id'],
            system_prompt=responder_prompt,
            building_time_ms=elapsed_ms,
            success=True,
        )

        graph_state['success'] = True

        logger.info(
            f"System prompts built: {len(response.personalities)} personas in {elapsed_ms:.2f}ms"
        )

        return graph_state
