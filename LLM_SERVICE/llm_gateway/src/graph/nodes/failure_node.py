from __future__ import annotations
import time
from src.core.logging import QuestionLogger
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.domain.models import GraphState


class FailureNode:
    def __init__(self) -> None:
        pass


    async def execute_node(self, state: "GraphState") -> "GraphState":
        state["success"] = False
        state["error"] = state.get("retrieval_error", "Context retrieval failed")

        total_ms = (time.time() * 1000) - state.get("started_at_ms", time.time() * 1000)
        QuestionLogger.log_question_processing(
            question_id=state["question_id"],
            original_question=state["query"].raw_text,
            context_chunks=[],
            llm_response="",
            processing_time_ms=total_ms,
            success=False,
            error_message=state["error"]
        )

        return state
