from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.logging import ContextRetrievalLogger
from src.pydantic_schemas.agent_controller import ContextChunk, RetrieveRequest, RetrieveResponse
from src.agents_graphs.graph_tools import GraphTools
from src.core.handlers import ResponseHandler
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.adapters.retriever_adapter import RetrieverAdapter
    from src.pydantic_schemas.agent_controller import GraphState


class RetrievalNode(BaseNode):
    def __init__(self, retriever_adapter: RetrieverAdapter) -> None:
        super().__init__('RETRIEVAL_NODE_TIMEOUT_SEC', 120.0, 2)
        self.retriever_adapter = retriever_adapter


    def _get_node_name(self) -> str:
        return 'retrieve_context'


    async def _execute_impl(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        request = RetrieveRequest(
            question=graph_state['query'].raw_text,
            collection_name=graph_state['collection_name'],
        )

        response: RetrieveResponse = await self.retriever_adapter.retrieve_context(request)
        
        graph_state['retrieval_success'] = bool(response.success and response.results)
        graph_state['retrieval_error'] = response.error or ''

        chunks: list[ContextChunk] = []
        if response.success:
            chunks = [
                ContextChunk(
                    doc_id=item.doc_id,
                    paragraph_id=item.paragraph_id,
                    chunk_id=item.chunk_id,
                    text=item.text,
                    pages=item.pages,
                    score=item.score,
                )
                for item in response.results
            ]

        graph_state['context_chunks'] = chunks

        if not graph_state['retrieval_success']:
            return ResponseHandler.handle_failure(
                graph_state,
                response.error or 'Context retrieval failed',
                error_key='retrieval_success'
            )

        return ResponseHandler.handle_success(
            graph_state,
            'retrieval_success',
            additional_data={'retrieval_error': ''}
        )


    def _log_success(
        self,
        graph_state: "GraphState",
        elapsed_ms: float
    ) -> None:
        payload = GraphTools.context_chunks_to_payload(graph_state['context_chunks'])
        ContextRetrievalLogger.log_context_retrieval(
            question_id=graph_state['question_id'],
            query=graph_state['query'].raw_text,
            retrieved_chunks=payload,
            retrieval_time_ms=elapsed_ms,
            success=graph_state['retrieval_success'],
            error_message=graph_state['retrieval_error'],
        )


    def _log_error(
        self,
        graph_state: "GraphState",
        elapsed_ms: float,
        error: str
    ) -> None:
        payload = GraphTools.context_chunks_to_payload(graph_state.get('context_chunks', []))
        ContextRetrievalLogger.log_context_retrieval(
            question_id=graph_state['question_id'],
            query=graph_state['query'].raw_text,
            retrieved_chunks=payload,
            retrieval_time_ms=elapsed_ms,
            success=False,
            error_message=error,
        )


