from __future__ import annotations
import time
from typing import TYPE_CHECKING

from src.core.logging import ContextRetrievalLogger
from src.domain.models import RetrieveRequest
from src.graph.graph_utils import timeout_and_retry

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.adapters.retriever_adapter import RetrieverAdapter
    from src.domain.models import GraphState


class RetrievalNode:
    def __init__(self, retriever_service: "RetrieverAdapter") -> None:
        self.retriever_service = retriever_service


    @timeout_and_retry(max_attempts=3, timeout_sec=25.0)
    async def execute_node(self, graph_state: "GraphState") -> "GraphState":
        time_start_node = time.time()
        request = graph_state["request"]
        question_id = graph_state["question_id"]
        collection_name = graph_state["collection_name"]

        retrieve_request = RetrieveRequest(
            query=request.question,
            collection_name=collection_name
        )
        
        response = await self.retriever_service.retrieve_context(retrieve_request)

        graph_state["retrieval_success"] = bool(response.success and response.results)
        graph_state["retrieval_error"] = response.error or ""
        graph_state["context_chunks"] = response.results if response.success else []

        elapsed = (time.time() - time_start_node) * 1000

        graph_state["timings_ms"]["retrieve_context"] = elapsed

        ContextRetrievalLogger.log_context_retrieval(
            question_id=question_id,
            query=request.question,
            retrieved_chunks=[c.to_json() for c in (response.results or [])] if response.success else [],
            retrieval_time_ms=elapsed,
            success=response.success,
            error_message=response.error or ""
        )

        return graph_state


