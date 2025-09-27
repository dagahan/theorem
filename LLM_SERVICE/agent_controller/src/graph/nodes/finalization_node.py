from __future__ import annotations
import time
from loguru import logger
from src.core.logging import QuestionLogger
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.domain.models import GraphState


class FinalizationNode:
    def __init__(self) -> None:
        pass


    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        total_ms = (time.time() * 1000) - graph_state.get("started_at_ms", time.time() * 1000)

        graph_state["success"] = bool(graph_state.get("llm_success", False))
        graph_state["error"] = "" if graph_state["success"] else (graph_state.get("llm_error") or graph_state.get("retrieval_error") or "Unknown error")

        QuestionLogger.log_question_processing(
            question_id=graph_state["question_id"],
            original_question=graph_state["query"].raw_text,
            context_chunks=[
                {
                    "doc_id": c.doc_id,
                    "paragraph_id": c.paragraph_id,
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "pages": c.pages,
                    "score": c.score
                }
                for c in graph_state.get("context_chunks", [])
            ],
            llm_response=graph_state.get("llm_answer", ""),
            processing_time_ms=total_ms,
            success=graph_state["success"],
            error_message=graph_state["error"]
        )

        logger.info(f"Question finalized: success={graph_state['success']}, total_time={total_ms:.2f}ms, chunks={len(graph_state.get('context_chunks', []))}")

        return graph_state
