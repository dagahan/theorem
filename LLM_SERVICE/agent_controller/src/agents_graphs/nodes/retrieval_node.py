from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from src.core.logging import ContextRetrievalLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.pydantic_schemas.agent_controller import ContextChunk, RetrieveRequest, RetrieveResponse
from src.agents_graphs.graph_tools import GraphTools

if TYPE_CHECKING:
    from src.adapters.retriever_adapter import RetrieverAdapter
    from src.pydantic_schemas.agent_controller import GraphState


class RetrievalNode:
    def __init__(self, retriever_adapter: RetrieverAdapter) -> None:
        self.retriever_adapter = retriever_adapter


    _TIMEOUT_SEC = TimeoutTools.get_timeout('RETRIEVAL_NODE_TIMEOUT_SEC', 120.0)


    @timeout_and_retry(max_attempts=2, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        started_at = time.time()

        request = RetrieveRequest(
            question=graph_state.get('expanded_question', graph_state['query'].raw_text),
            collection_name=graph_state['collection_name'],
        )

        try:
            response: RetrieveResponse = await self.retriever_adapter.retrieve_context(request)
            
        except Exception as ex:  # noqa: BLE001
            graph_state['retrieval_success'] = False
            graph_state['retrieval_error'] = f"{ex}"
            return GraphTools.mark_failure(graph_state, f'Retrieval failed: {ex}')

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

        elapsed_ms = GraphTools.record_timing(graph_state, 'retrieve_context', started_at)
        payload = GraphTools.context_chunks_to_payload(chunks)

        ContextRetrievalLogger.log_context_retrieval(
            question_id=graph_state['question_id'],
            query=graph_state['query'].raw_text,
            retrieved_chunks=payload,
            retrieval_time_ms=elapsed_ms,
            success=response.success,
            error_message=response.error or '',
        )

        logger.info(
            f"Context retrieved: {len(chunks)} chunks in {elapsed_ms:.2f}ms, "
            f"success={response.success}"
        )

        if not graph_state['retrieval_success']:
            GraphTools.mark_failure(graph_state, response.error or 'Context retrieval failed')

        return graph_state
