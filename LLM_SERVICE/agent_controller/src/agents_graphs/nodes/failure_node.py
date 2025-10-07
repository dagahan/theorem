from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.core.logging import QuestionLogger
from src.agents_graphs.graph_tools import GraphTools

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState


class FailureNode:
    def __init__(self) -> None:
        pass


    async def execute_node(
        self,
        state: GraphState
    ) -> GraphState:
        error_message = (
            state.get('response_error')
            or state.get('retrieval_error')
            or state.get('error')
            or 'Pipeline failed'
        )
        
        GraphTools.mark_failure(state, error_message)


        total_ms = GraphTools.total_elapsed_ms(state)

        QuestionLogger.log_question_processing(
            question_id=state['question_id'],
            question=state['query'].raw_text,
            context_chunks=[],
            response_answer='',
            processing_time_ms=total_ms,
            success=False,
            error_message=error_message,
        )

        logger.error(f"Question failed: {error_message}, total_time={total_ms:.2f}ms")

        return state
