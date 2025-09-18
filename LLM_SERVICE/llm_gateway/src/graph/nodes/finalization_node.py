from __future__ import annotations
import time
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
            original_question=graph_state["request"].question,
            context_chunks=[c.to_json() for c in graph_state.get("context_chunks", [])],
            llm_response=graph_state.get("llm_answer", ""),
            processing_time_ms=total_ms,
            success=graph_state["success"],
            error_message=graph_state["error"]
        )

        return graph_state
