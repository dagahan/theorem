from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.logging import ResponderGenerationLogger
from src.core.schema_utils import get_utils
from src.services.llm_model import LLMModel
from src.agents_graphs.graph_tools import GraphTools
from src.core.handlers import ResponseHandler
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import Personality, InferenceParams, ContextDigestItem, GraphState, QuestionResponse, Personalities
    from src.adapters.vllm_adapter import VLLMAdapter


class ResponseAnswerNode(BaseNode):
    def __init__(self, vllm_adapter: "VLLMAdapter", defaults: "InferenceParams") -> None:
        super().__init__('LLM_GENERATION_NODE_TIMEOUT_SEC', 90.0, 3)
        self.llm_model = LLMModel(adapter=vllm_adapter)
        self.defaults = defaults
        self.schema_utils = get_utils()


    def _get_node_name(self) -> str:
        return 'llm_generation'


    async def _execute_impl(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        personalities = graph_state.get('personalities')
        if not personalities or 'Responder' not in personalities.personalities:
            return ResponseHandler.handle_failure(
                graph_state,
                "Responder personality is missing",
                error_key='response_success'
            )

        responder_personality = personalities.personalities['Responder']
        system_prompt = responder_personality.system_prompt

        question = graph_state.get('question', graph_state['query'].raw_text)
        context_json = GraphTools.digests_to_json(graph_state.get('context_digests', []))
        stream = bool(graph_state['query'].stream)

        params: "InferenceParams" = graph_state.get('inference_params', self.defaults)

        if responder_personality.response_schema is None or stream:
            text = await self.llm_model.infer(
                system_prompt=system_prompt,
                question=question,
                context=context_json,
                stream=stream,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
            )

            return ResponseHandler.handle_success(
                graph_state,
                'response_success',
                additional_data={
                    'response_answer': text,
                    'response_error': ''
                }
            )

        else:
            response_model = self.schema_utils.get_personality_model(
                responder_personality.model_dump(), 
                "ResponderResponse"
            )
            
            if response_model is None:
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
                    answer = str(result.model_dump_json())

            return ResponseHandler.handle_success(
                graph_state,
                'response_success',
                additional_data={
                    'response_answer': answer,
                    'response_error': ''
                }
            )



    def _log_success(
        self,
        graph_state: "GraphState",
        elapsed_ms: float
    ) -> None:
        ResponderGenerationLogger.log_responder_generation(
            question_id=graph_state['question_id'],
            question=graph_state['query'].raw_text,
            context=GraphTools.digests_to_json(graph_state.get('context_digests', [])),
            response_answer=graph_state['response_answer'],
            generation_time_ms=elapsed_ms,
            success=graph_state['response_success'],
            error_message=graph_state['response_error'],
        )


    def _log_error(
        self,
        graph_state: "GraphState",
        elapsed_ms: float,
        error: str
    ) -> None:
        ResponderGenerationLogger.log_responder_generation(
            question_id=graph_state['question_id'],
            question=graph_state['query'].raw_text,
            context=GraphTools.digests_to_json(graph_state.get('context_digests', [])),
            response_answer='',
            generation_time_ms=elapsed_ms,
            success=False,
            error_message=error,
        )


