from __future__ import annotations

import time
from typing import TYPE_CHECKING
from loguru import logger
from src.core.logging import QuestionBuilderLogger
from src.graph.graph_utils import timeout_and_retry
from src.domain.models import QuestionBuilderRequest, QuestionBuilderResponse

if TYPE_CHECKING:
    from src.adapters.question_builder_adapter import QuestionBuilderAdapter
    from src.domain.models import GraphState


class QuestionBuilderNode:
    def __init__(self, question_builder_adapter: "QuestionBuilderAdapter") -> None:
        self.adapter = question_builder_adapter


    @timeout_and_retry(max_attempts=3, timeout_sec=25.0)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()

        request = QuestionBuilderRequest(raw_text=graph_state["query"].raw_text)
        response: QuestionBuilderResponse = await self.adapter.process_question(request)

        if not response.success:
            graph_state["success"] = False
            graph_state["error"] = f"Question processing failed: {response.error or 'unknown'}"
            return graph_state

        graph_state["original_question"] = response.original_question
        graph_state["expanded_question"] = response.expanded_question
        graph_state["expanded_question_semantic_parts"] = response.expanded_question_semantic_parts

        elapsed = (time.time() - execution_start_time) * 1000.0
        graph_state.setdefault("timings_ms", {})["build_question"] = elapsed

        QuestionBuilderLogger.log_question_building(
            question_id=graph_state["question_id"],
            original_question=response.original_question,
            expanded_question=response.expanded_question,
            semantic_parts=response.expanded_question_semantic_parts,
            building_time_ms=elapsed,
            success=True
        )

        logger.info(f"Question processed: original='{response.original_question}', expanded='{response.expanded_question}', parts={len(response.expanded_question_semantic_parts)}")

        return graph_state


