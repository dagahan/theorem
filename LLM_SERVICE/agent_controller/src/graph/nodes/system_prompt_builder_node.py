from __future__ import annotations
import time
from typing import TYPE_CHECKING
from loguru import logger
from src.core.logging import SystemPromptBuilderLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools

if TYPE_CHECKING:
    from src.adapters.system_prompt_builder_adapter import SystemPromptBuilderAdapter
    from src.domain.models import GraphState, SystemPromptResponse


class SystemPromptBuilderNode:
    def __init__(self, adapter: "SystemPromptBuilderAdapter") -> None:
        self.adapter = adapter


    _TIMEOUT_SEC = TimeoutTools.get_timeout('SYSTEM_PROMPT_NODE_TIMEOUT_SEC', 15.0)


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()

        response: SystemPromptResponse = await self.adapter.build_system_prompt()

        if not response.success:
            graph_state["success"] = False
            graph_state["error"] = f"System prompt building failed: {response.error or 'unknown'}"
            return graph_state

        graph_state["system_prompt"] = response.system_prompt
        elapsed = (time.time() - execution_start_time) * 1000.0
        graph_state.setdefault("timings_ms", {})["build_system_prompt"] = elapsed

        SystemPromptBuilderLogger.log_system_prompt_building(
            question_id=graph_state["question_id"],
            system_prompt=response.system_prompt,
            building_time_ms=elapsed,
            success=True
        )

        logger.info(f"System prompt built: {len(response.system_prompt)} chars in {elapsed:.2f}ms")

        return graph_state
