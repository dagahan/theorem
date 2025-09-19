from __future__ import annotations

import time
from typing import TYPE_CHECKING
from loguru import logger

from src.core.logging import ContextRetrievalLogger
from src.graph.graph_utils import timeout_and_retry
from src.domain.models import QuestionBuilderRequest

if TYPE_CHECKING:
    from src.adapters.question_builder_adapter import QuestionBuilderAdapter
    from src.domain.models import GraphState


class QuestionBuilderNode:
    def __init__(self, question_builder_service: "QuestionBuilderAdapter") -> None:
        self.question_builder_service = question_builder_service


    @timeout_and_retry(max_attempts=3, timeout_sec=25.0)
    async def execute_node(self, graph_state: "GraphState") -> "GraphState":
        time_start_node = time.time()
        query = graph_state["query"]

        question_request = QuestionBuilderRequest(raw_text=query.raw_text)

        result = await self.question_builder_service.process_question(question_request)

        if not result.success:
            graph_state["success"] = False
            graph_state["error"] = f"Question processing failed: {result.error}"
            return graph_state

        graph_state["original_question"] = result.original_question
        graph_state["expanded_question"] = result.expanded_question
        graph_state["expanded_question_semantic_parts"] = result.expanded_question_semantic_parts

        elapsed = (time.time() - time_start_node) * 1000
        graph_state["timings_ms"]["build_question"] = elapsed

        logger.info(f"Question processed: original='{result.original_question}', "
                   f"expanded='{result.expanded_question}', "
                   f"parts={len(result.expanded_question_semantic_parts)}")

        return graph_state


