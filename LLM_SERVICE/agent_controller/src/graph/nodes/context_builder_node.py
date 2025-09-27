from __future__ import annotations

import time
from typing import TYPE_CHECKING, List
from loguru import logger
from src.core.logging import ContextBuilderLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.domain.models import ContextBuilderRequest, ContextBuilderResponse, ContextChunk

if TYPE_CHECKING:
    from src.adapters.context_builder_adapter import ContextBuilderAdapter
    from src.domain.models import GraphState


class ContextBuilderNode:
    def __init__(self, context_builder_adapter: "ContextBuilderAdapter") -> None:
        self.adapter = context_builder_adapter


    _TIMEOUT_SEC = TimeoutTools.get_timeout('CONTEXT_BUILDER_NODE_TIMEOUT_SEC', 60.0)


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()

        context_chunks: List[ContextChunk] = graph_state.get("context_chunks", [])
        max_chars = graph_state.get("max_context_chars", 4000)

        request = ContextBuilderRequest(
            chunks=context_chunks,
            max_context_chars=max_chars
        )

        response: ContextBuilderResponse = await self.adapter.build_context(request)

        if not response.success:
            graph_state["context_text"] = "CTX error"
            graph_state["error"] = f"Context building failed: {response.error or 'unknown'}"
            graph_state.setdefault("timings_ms", {})["build_context_text"] = (time.time() - execution_start_time) * 1000.0
            return graph_state

        graph_state["context_text"] = response.context_text
        elapsed = (time.time() - execution_start_time) * 1000.0
        graph_state.setdefault("timings_ms", {})["build_context_text"] = elapsed

        ContextBuilderLogger.log_context_building(
            question_id=graph_state["question_id"],
            input_chunks_count=len(context_chunks),
            context_text=response.context_text,
            building_time_ms=elapsed,
            success=True
        )

        logger.info(f"Context built: {len(context_chunks)} chunks -> {len(response.context_text)} chars in {elapsed:.2f}ms")

        return graph_state

