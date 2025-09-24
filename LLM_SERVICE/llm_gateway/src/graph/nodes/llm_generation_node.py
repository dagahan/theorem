from __future__ import annotations
import time
from typing import TYPE_CHECKING
from loguru import logger
from src.core.logging import LLMGenerationLogger
from src.graph.graph_utils import timeout_and_retry

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter
    from src.domain.models import GraphState, QuestionResponse


class LLMGenerationNode:
    def __init__(self, vllm_adapter: "VLLMAdapter") -> None:
        self.vllm = vllm_adapter


    @timeout_and_retry(max_attempts=3, timeout_sec=60.0)
    async def execute_node(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        execution_start_time = time.time()

        system_prompt = graph_state["system_prompt"]
        context_text = graph_state.get("context_text", "")
        question = graph_state.get("original_question", graph_state["query"].raw_text)

        response: QuestionResponse = await self.vllm.generate_answer(
            question=question,
            system_prompt=system_prompt,
            context=context_text,
            stream=graph_state["query"].stream
        )

        graph_state["llm_answer"] = response.answer or ""
        graph_state["llm_success"] = bool(response.success)
        graph_state["llm_error"] = response.error or ""

        elapsed = (time.time() - execution_start_time) * 1000.0
        graph_state.setdefault("timings_ms", {})["llm_generation"] = elapsed

        LLMGenerationLogger.log_llm_generation(
            question_id=graph_state["question_id"],
            question=graph_state["query"].raw_text,
            context=system_prompt,
            llm_response=response.answer,
            generation_time_ms=elapsed,
            success=response.success,
            error_message=response.error or ""
        )

        logger.info(f"LLM generation completed: {len(response.answer)} chars in {elapsed:.2f}ms, success={response.success}")

        return graph_state

