from __future__ import annotations
import time
from typing import TYPE_CHECKING
from loguru import logger
from src.core.logging import ContextRetrievalLogger
from src.graph.graph_utils import timeout_and_retry
from src.domain.models import RetrieveRequest, RetrieveResponse, ContextChunk

if TYPE_CHECKING:
    from src.adapters.retriever_adapter import RetrieverAdapter
    from src.domain.models import GraphState


class RetrievalNode:
    def __init__(self, retriever_adapter: "RetrieverAdapter") -> None:
        self.retriever_adapter = retriever_adapter


    @timeout_and_retry(max_attempts=3, timeout_sec=25.0)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()

        query = graph_state["query"]
        collection_name = graph_state["collection_name"]

        expanded_question = graph_state.get("expanded_question", query.raw_text)

        request = RetrieveRequest(question=expanded_question, collection_name=collection_name)
        response: RetrieveResponse = await self.retriever_adapter.retrieve_context(request)

        graph_state["retrieval_success"] = bool(response.success and response.results)
        graph_state["retrieval_error"] = response.error or ""

        context_chunks = [
            ContextChunk(
                doc_id=r.doc_id,
                paragraph_id=r.paragraph_id,
                chunk_id=r.chunk_id,
                text=r.text,
                pages=r.pages,
                score=r.score
            )
            for r in (response.results if response.success else [])
        ]

        graph_state["context_chunks"] = context_chunks

        elapsed = (time.time() - execution_start_time) * 1000.0
        graph_state.setdefault("timings_ms", {})["retrieve_context"] = elapsed

        ContextRetrievalLogger.log_context_retrieval(
            question_id=graph_state["question_id"],
            query=query.raw_text,
            retrieved_chunks=[{
                "doc_id": c.doc_id,
                "paragraph_id": c.paragraph_id,
                "chunk_id": c.chunk_id,
                "text": c.text,
                "pages": c.pages,
                "score": c.score
            }
            for c in context_chunks],
            retrieval_time_ms=elapsed,
            success=response.success,
            error_message=response.error or ""
        )

        logger.info(f"Context retrieved: {len(context_chunks)} chunks in {elapsed:.2f}ms, success={response.success}")

        return graph_state


