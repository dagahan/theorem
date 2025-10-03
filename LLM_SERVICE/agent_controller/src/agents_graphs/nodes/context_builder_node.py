from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from loguru import logger

from src.core.logging import ContextBuilderLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.pydantic_schemas.agent_controller import ContextBuilderRequest, ContextBuilderResponse, ContextChunk, GraphState
from src.agents_graphs.graph_tools import GraphTools

if TYPE_CHECKING:
    from src.adapters.context_builder_adapter import ContextBuilderAdapter


class ContextBuilderNode:
    def __init__(self, context_builder_adapter: ContextBuilderAdapter) -> None:
        self.adapter = context_builder_adapter
        self._fallback_max_context_chars = GraphTools.resolve_default_max_context_chars()


    _TIMEOUT_SEC = TimeoutTools.get_timeout('CONTEXT_BUILDER_NODE_TIMEOUT_SEC', 180.0)


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        started_at = time.time()

        chunks: list[ContextChunk] = graph_state.get('context_chunks', [])
        if not chunks:
            graph_state['context_digests'] = []
            elapsed_ms = GraphTools.record_timing(graph_state, 'build_context_text', started_at)
            ContextBuilderLogger.log_context_building(
                question_id=graph_state['question_id'],
                input_chunks_count=0,
                digests=[],
                building_time_ms=elapsed_ms,
                success=True,
            )

            logger.info(
                f"Context building skipped: no chunks provided in {elapsed_ms:.2f}ms"
            )

            graph_state['success'] = True

            return graph_state

        prompts = graph_state.get('personality_prompts') or {}

        summarizer_prompt = prompts.get('Summarizer', '').strip()

        if not summarizer_prompt:
            elapsed_ms = GraphTools.record_timing(graph_state, 'build_context_text', started_at)
            ContextBuilderLogger.log_context_building(
                question_id=graph_state['question_id'],
                input_chunks_count=len(chunks),
                digests=[],
                building_time_ms=elapsed_ms,
                success=False,
                error_message='Missing Summarizer prompt',
            )

            logger.error(
                f"Context building failed: Missing Summarizer prompt in {elapsed_ms:.2f}ms"
            )

            GraphTools.mark_failure(
                graph_state,
                'Missing Summarizer prompt'
            )

            graph_state['context_digests'] = []

            return graph_state

        max_context_chars = GraphTools.resolve_max_context_chars(
            graph_state.get('max_context_chars'),
            self._fallback_max_context_chars,
        )

        graph_state['max_context_chars'] = max_context_chars

        request = ContextBuilderRequest(
            chunks=chunks,
            max_context_chars=max_context_chars,
            summarizer_prompt=summarizer_prompt,
        )

        try:
            response: ContextBuilderResponse = await self.adapter.build_context(request)

        except Exception as ex:  # noqa: BLE001
            elapsed_ms = GraphTools.record_timing(graph_state, 'build_context_text', started_at)

            ContextBuilderLogger.log_context_building(
                question_id=graph_state['question_id'],
                input_chunks_count=len(chunks),
                digests=[],
                building_time_ms=elapsed_ms,
                success=False,
                error_message=f"{ex}",
            )

            logger.error(f'Context building failed: {ex} in {elapsed_ms:.2f}ms')

            graph_state['context_digests'] = []

            return GraphTools.mark_failure(graph_state, f'Context building failed: {ex}')

        elapsed_ms = GraphTools.record_timing(graph_state, 'build_context_text', started_at)

        if not response.success:
            ContextBuilderLogger.log_context_building(
                question_id=graph_state['question_id'],
                input_chunks_count=len(chunks),
                digests=[],
                building_time_ms=elapsed_ms,
                success=False,
                error_message=response.error or 'unknown',
            )

            error_text = response.error or 'unknown'

            logger.error(
                f"Context building failed: {error_text} in {elapsed_ms:.2f}ms"
            )

            graph_state['context_digests'] = []

            return GraphTools.mark_failure(
                graph_state,
                f'Context building failed: {error_text}'
            )

        graph_state['context_digests'] = response.digests

        ContextBuilderLogger.log_context_building(
            question_id=graph_state['question_id'],
            input_chunks_count=len(chunks),
            digests=response.digests,
            building_time_ms=elapsed_ms,
            success=True,
        )

        graph_state['success'] = True

        logger.info(
            (
                f"Context built: {len(response.digests)} digests summarising {len(chunks)} chunks "
                f"in {elapsed_ms:.2f}ms"
            )
        )

        return graph_state
