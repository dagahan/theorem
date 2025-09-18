from __future__ import annotations
import time
from typing import TYPE_CHECKING

from src.services.text_normalizer import TextNormalizer
if TYPE_CHECKING:
    from src.domain.models import GraphState


class QuestionValidationNode:
    def __init__(self) -> None:
        self.text_normalizer = TextNormalizer()


    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        time_start_node = time.time()
        
        request = graph_state["request"]

        if not request.question or not request.question.strip():
            graph_state["success"] = False
            graph_state["error"] = "Question is empty."
            return graph_state

        normalized = self.text_normalizer.normalize_question_text(request.question)

        graph_state["normalized_question"] = normalized

        graph_state["timings_ms"]["validate_and_prepare"] = (time.time() - time_start_node) * 1000

        return graph_state


