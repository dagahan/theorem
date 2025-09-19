from __future__ import annotations
import time
from typing import TYPE_CHECKING

from src.core.logging import LLMGenerationLogger
from src.graph.graph_utils import timeout_and_retry
if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter
    from src.domain.models import GraphState


class LLMGenerationNode:
    def __init__(self, llm_service: "VLLMAdapter") -> None:
        self.vllm_adapter_service = llm_service


    @timeout_and_retry(max_attempts=3, timeout_sec=60.0)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()

        query = graph_state["query"]
        question_id = graph_state["question_id"]
        context_text = graph_state.get("context_text", "")

        question_for_llm = graph_state.get("original_question", query.raw_text)

        llm_generation_response = await self.vllm_adapter_service.generate_answer(
            question_for_llm,
            context_text,
            query.stream
        )

        graph_state["llm_answer"] = llm_generation_response.answer or ""
        graph_state["llm_success"] = bool(llm_generation_response.success)
        graph_state["llm_error"] = llm_generation_response.error or ""

        generation_execution_time_ms = (time.time() - execution_start_time) * 1000

        graph_state["timings_ms"]["llm_generation"] = generation_execution_time_ms

        LLMGenerationLogger.log_llm_generation(
            question_id=question_id,
            question=query.raw_text,
            context=context_text,
            llm_response=llm_generation_response.answer,
            generation_time_ms=generation_execution_time_ms,
            success=llm_generation_response.success,
            error_message=llm_generation_response.error or ""
        )

        return graph_state
