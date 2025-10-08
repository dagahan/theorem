from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.logging import ResponderGenerationLogger
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
        self.llm_model = LLMModel(vllm_adapter=vllm_adapter)
        self.defaults = defaults


    def _get_node_name(self) -> str:
        return 'llm_generation'


    async def _execute_impl(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        personalities = graph_state.get('personalities')
        if not personalities or 'responder' not in personalities.personalities:
            return ResponseHandler.handle_failure(
                graph_state,
                "responder personality is missing",
                error_key='response_success'
            )

        responder_personality = personalities.personalities['responder']
        system_prompt = responder_personality.system_prompt

        question = graph_state.get('question', '')
        context_json = GraphTools.digests_to_json(graph_state.get('context_digests', []))
        stream = False

        params: "InferenceParams" = graph_state.get('inference_params', self.defaults)

        # Always use infer() for responder since it doesn't have response_schema
        text = await self.llm_model.infer(
            system_prompt=system_prompt,
            question=question,
            context=context_json,
            stream=stream,
            temperature=params.temperature,
            max_tokens=params.max_tokens,
            mcp_server=graph_state.get('mcp_server'),
        )

        graph_state['response_answer'] = text
        graph_state['response_success'] = True
        graph_state['response_error'] = ''
        
        return ResponseHandler.handle_success(
            graph_state,
            'response_success',
            additional_data={
                'response_answer': text,
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
            question=graph_state.get('question', ''),
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
            question=graph_state.get('question', ''),
            context=GraphTools.digests_to_json(graph_state.get('context_digests', [])),
            response_answer='',
            generation_time_ms=elapsed_ms,
            success=False,
            error_message=error,
        )


