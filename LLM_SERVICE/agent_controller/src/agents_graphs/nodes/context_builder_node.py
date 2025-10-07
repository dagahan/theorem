from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.logging import ContextBuilderLogger
from src.pydantic_schemas.agent_controller import ContextBuilderRequest, ContextBuilderResponse, ContextChunk, GraphState
from src.agents_graphs.graph_tools import GraphTools
from src.core.handlers import ResponseHandler
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.adapters.context_builder_adapter import ContextBuilderAdapter


class ContextBuilderNode(BaseNode):
    def __init__(self, context_builder_adapter: ContextBuilderAdapter) -> None:
        super().__init__('CONTEXT_BUILDER_NODE_TIMEOUT_SEC', 180.0, 3)
        self.adapter = context_builder_adapter
        self._fallback_max_context_chars = GraphTools.resolve_default_max_context_chars()


    def _get_node_name(self) -> str:
        return 'build_context_text'


    async def _execute_impl(self, graph_state: GraphState) -> GraphState:
        chunks: list[ContextChunk] = graph_state.get('context_chunks', [])
        if not chunks:
            graph_state['context_digests'] = []
            return ResponseHandler.handle_success(graph_state, 'success')

        personalities = graph_state.get('personalities')
        if not personalities or 'Summarizer' not in personalities.personalities:
            return ResponseHandler.handle_failure(
                graph_state, 
                "Summarizer personality is missing",
                additional_data={'context_digests': []}
            )

        summarizer = personalities.personalities['Summarizer']
        summarizer_prompt = summarizer.system_prompt.strip()

        if not summarizer_prompt:
            return ResponseHandler.handle_failure(
                graph_state, 
                'Missing Summarizer prompt',
                additional_data={'context_digests': []}
            )

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

        response: ContextBuilderResponse = await self.adapter.build_context(request)
        
        return ResponseHandler.process_response(
            graph_state=graph_state,
            response=response,
            success_key='success',
            success_data={'context_digests': response.digests},
            failure_data={'context_digests': []},
            operation_name='Context building'
        )

    def _log_success(self, graph_state: GraphState, elapsed_ms: float) -> None:
        ContextBuilderLogger.log_context_building(
            question_id=graph_state['question_id'],
            input_chunks_count=len(graph_state.get('context_chunks', [])),
            digests=graph_state['context_digests'],
            building_time_ms=elapsed_ms,
            success=True,
        )

    def _log_error(self, graph_state: GraphState, elapsed_ms: float, error: str) -> None:
        ContextBuilderLogger.log_context_building(
            question_id=graph_state['question_id'],
            input_chunks_count=len(graph_state.get('context_chunks', [])),
            digests=[],
            building_time_ms=elapsed_ms,
            success=False,
            error_message=error,
        )
