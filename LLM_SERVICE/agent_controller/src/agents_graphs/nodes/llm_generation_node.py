from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from src.core.logging import LLMGenerationLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.agents_graphs.graph_tools import GraphTools
from src.services.personality_client import PersonalityClient

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter
    from src.pydantic_schemas.agent_controller import ContextDigestItem, GraphState, QuestionResponse


class LLMGenerationNode:
    def __init__(self, vllm_adapter: VLLMAdapter) -> None:
        self.personality_client = PersonalityClient(vllm_adapter)


    _TIMEOUT_SEC = TimeoutTools.get_timeout('LLM_GENERATION_NODE_TIMEOUT_SEC', 90.0)


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: GraphState,
    ) -> GraphState:
        started_at = time.time()

        personality_prompts: dict[str, str] = graph_state.get('personality_prompts', {}) or {}
        digests: list[ContextDigestItem] = graph_state.get('context_digests', []) or []
        context_payload = GraphTools.digests_to_json(digests)

        question = graph_state.get('original_question', graph_state['query'].raw_text)
        agent_name = graph_state.get('agent_name', 'unknown')

        try:
            response: QuestionResponse = await self.personality_client.generate(
                personality_name='Responder',
                personality_prompts=personality_prompts,
                question=question,
                context=context_payload,
                stream=graph_state['query'].stream,
                agent_name=agent_name,
            )
            
        except ValueError as ex:
            logger.error(f"{ex}")
            GraphTools.mark_failure(graph_state, f"{ex}")
            return graph_state

        graph_state['llm_answer'] = response.answer or ''
        graph_state['llm_success'] = bool(response.success)
        graph_state['llm_error'] = response.error or ''

        elapsed_ms = GraphTools.record_timing(graph_state, 'llm_generation', started_at)

        LLMGenerationLogger.log_llm_generation(
            question_id=graph_state['question_id'],
            question=graph_state['query'].raw_text,
            context=context_payload,
            llm_response=response.answer,
            generation_time_ms=elapsed_ms,
            success=response.success,
            error_message=response.error or '',
        )

        logger.info(
            f"LLM generation completed: {len(response.answer)} chars in {elapsed_ms:.2f}ms, "
            f"success={response.success}"
        )

        if not response.success:
            GraphTools.mark_failure(graph_state, response.error or 'LLM generation failed')

        return graph_state
