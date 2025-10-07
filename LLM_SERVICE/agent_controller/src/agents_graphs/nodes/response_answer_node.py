from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from src.core.logging import ResponderGenerationLogger
from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.agents_graphs.graph_tools import GraphTools
from src.core.schema_utils import get_utils
from src.services.llm_model import LLMModel

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import Personality, InferenceParams, ContextDigestItem, GraphState, QuestionResponse, Personalities
    from src.adapters.vllm_adapter import VLLMAdapter



class ResponseAnswerNode:
    def __init__(self, vllm_adapter: "VLLMAdapter", defaults: "InferenceParams") -> None:
        self.llm_model = LLMModel(adapter=vllm_adapter)
        self.defaults = defaults
        self.schema_utils = get_utils()
        


    _TIMEOUT_SEC = TimeoutTools.get_timeout('LLM_GENERATION_NODE_TIMEOUT_SEC', 90.0)


    @timeout_and_retry(max_attempts=3, timeout_sec=_TIMEOUT_SEC)
    async def execute_node(
        self,
        graph_state: "GraphState",
    ) -> "GraphState":
        started_at = time.time()

        personalities = graph_state.get('personalities')
        if not personalities or 'Responder' not in personalities.personalities:
            return GraphTools.mark_failure(graph_state, "Responder personality is missing")

        responder_personality = personalities.personalities['Responder']
        system_prompt = responder_personality.system_prompt

        question = graph_state.get('question', graph_state['query'].raw_text)
        context_json = GraphTools.digests_to_json(graph_state.get('context_digests', []))
        stream = bool(graph_state['query'].stream)

        params: "InferenceParams" = graph_state.get('inference_params', self.defaults)

        try:
            if responder_personality.response_schema is None or stream:
                text = await self.llm_model.infer(
                    system_prompt=system_prompt,
                    question=question,
                    context=context_json,
                    stream=stream,
                    temperature=params.temperature,
                    max_tokens=params.max_tokens,
                )

                graph_state['response_answer'] = text
                graph_state['response_success'] = True
                graph_state['response_error'] = ''

            else:
                response_model = self.schema_utils.get_personality_model(
                    responder_personality.model_dump(), 
                    "ResponderResponse"
                )
                
                if response_model is None:
                    # Если нет схемы, используем стандартный ответ
                    answer: str = await self.llm_model.infer(
                        system_prompt=system_prompt,
                        question=question,
                        context=context_json,
                        stream=False,
                        temperature=params.temperature,
                        max_tokens=params.max_tokens,
                    )
                else:
                    result = await self.llm_model.pydantic_ai_request(
                        system_prompt=system_prompt,
                        question=question,
                        context=context_json,
                        response_schema=response_model,
                        retries=1,
                        temperature=params.temperature,
                        max_tokens=params.max_tokens,
                    )
                    answer_value = getattr(result, 'answer', None)
                    if isinstance(answer_value, str):
                        answer = answer_value
                    else:
                        answer = result.model_dump_json()

                graph_state['response_answer'] = answer
                graph_state['response_success'] = True
                graph_state['response_error'] = ''

        except Exception as ex:  # noqa: BLE001
            graph_state['response_answer'] = ''
            graph_state['response_success'] = False
            graph_state['response_error'] = f"{ex}"

        elapsed_ms = GraphTools.record_timing(graph_state, 'llm_generation', started_at)

        ResponderGenerationLogger.log_responder_generation(
            question_id=graph_state['question_id'],
            question=graph_state['query'].raw_text,
            context=context_json,
            response_answer=graph_state['response_answer'],
            generation_time_ms=elapsed_ms,
            success=graph_state['response_success'],
            error_message=graph_state['response_error'],
        )

        logger.info(
            f"LLM generation completed: {len(graph_state['response_answer'])} chars in {elapsed_ms:.2f}ms, "
            f"success={graph_state['response_success']}"
        )

        if not graph_state.get('response_success', False):
            GraphTools.mark_failure(graph_state, graph_state.get('response_error') or 'LLM generation failed')

        return graph_state


