from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

from loguru import logger

from src.core.logging import QuestionBuilderLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.pydantic_schemas.agent_controller import QuestionBuilderRequest, QuestionBuilderResponse
from src.agents_graphs.graph_tools import GraphTools

if TYPE_CHECKING:
    from src.adapters.question_builder_adapter import QuestionBuilderAdapter
    from src.pydantic_schemas.agent_controller import GraphState


class QuestionBuilderNode:
    def __init__(self, question_builder_adapter: QuestionBuilderAdapter) -> None:
        self.adapter = question_builder_adapter


    _TIMEOUT_SEC = TimeoutTools.get_timeout('QUESTION_BUILDER_NODE_TIMEOUT_SEC', 30.0)


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        started_at = time.time()
        request = QuestionBuilderRequest(raw_text=graph_state['query'].raw_text)

        try:
            response: QuestionBuilderResponse = await self.adapter.process_question(request)

        except TimeoutError:
            raise
            
        except Exception as ex:  # noqa: BLE001
            return GraphTools.mark_failure(graph_state, f'Question builder call failed: {ex}')

        if not response.success:
            error_text = response.error or 'unknown'
            return GraphTools.mark_failure(graph_state, f'Question processing failed: {error_text}')

        graph_state['original_question'] = response.original_question
        graph_state['expanded_question'] = response.expanded_question
        graph_state['expanded_question_semantic_parts'] = response.expanded_question_semantic_parts

        elapsed_ms = GraphTools.record_timing(graph_state, 'build_question', started_at)

        QuestionBuilderLogger.log_question_building(
            question_id=graph_state['question_id'],
            original_question=response.original_question,
            expanded_question=response.expanded_question,
            semantic_parts=response.expanded_question_semantic_parts,
            building_time_ms=elapsed_ms,
            success=True,
        )

        graph_state['success'] = True

        logger.info(
            (
                f"Question processed: original='{response.original_question}', "
                f"expanded='{response.expanded_question}', "
                f"parts={len(response.expanded_question_semantic_parts)}"
            )
        )

        return graph_state
