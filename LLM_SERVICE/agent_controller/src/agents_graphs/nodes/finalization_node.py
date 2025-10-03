from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.core.logging import QuestionLogger
from src.agents_graphs.graph_tools import GraphTools

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState


class FinalizationNode:
    def __init__(self) -> None:
        pass


    async def execute_node(
        self,
        graph_state: GraphState
    ) -> GraphState:
        total_ms = GraphTools.total_elapsed_ms(graph_state)

        graph_state['success'] = bool(graph_state.get('llm_success', False))
        
        if graph_state['success']:
            graph_state['error'] = ''

        else:
            graph_state['error'] = (
                graph_state.get('llm_error')
                or graph_state.get('retrieval_error')
                or 'Unknown error'
            )

        QuestionLogger.log_question_processing(
            question_id=graph_state['question_id'],
            original_question=graph_state['query'].raw_text,
            context_chunks=GraphTools.context_chunks_to_payload(
                graph_state.get('context_chunks', []),
            ),
            llm_response=graph_state.get('llm_answer', ''),
            processing_time_ms=total_ms,
            success=graph_state['success'],
            error_message=graph_state['error'],
        )

        logger.info(
            f"Question finalized: success={graph_state['success']}, total_time={total_ms:.2f}ms, "
            f"chunks={len(graph_state.get('context_chunks', []))}"
        )

        return graph_state
