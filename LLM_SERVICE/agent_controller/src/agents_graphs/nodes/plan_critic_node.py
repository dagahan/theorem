from __future__ import annotations

import json
from typing import TYPE_CHECKING

from loguru import logger

from src.core.handlers import ResponseHandler
from src.services.llm_model import LLMModel
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.vllm_adapter import VLLMAdapter


class PlanCriticNode(BaseNode):
    def __init__(self, vllm_adapter: "VLLMAdapter") -> None:
        super().__init__('PLAN_CRITIC_NODE_TIMEOUT_SEC', 10.0, 2)
        self.llm = LLMModel(vllm_adapter=vllm_adapter)


    def _get_node_name(self) -> str:
        return 'plan_critic'


    async def _execute_impl(self, state: "GraphState") -> "GraphState":
        personalities = state.get('personalities')
        if not personalities or 'response_critic' not in personalities.personalities:
            state['plan_ok'] = True
            return ResponseHandler.handle_success(state, 'success')

        persona = personalities.personalities['response_critic']
        system_prompt = persona.system_prompt
        response_schema = persona.response_schema
        if not response_schema or not isinstance(response_schema, dict):
            state['plan_ok'] = True
            return ResponseHandler.handle_success(state, 'success')

        question = state.get('question', '')
        context = json.dumps({
            "response_plan": state.get('response_plan', {}),
            "context_digests": [
                {"title": d.title, "summary": d.summary} 
                for d in state.get('context_digests', [])
            ],
        }, ensure_ascii=False)

        result = await self.llm.pydantic_ai_request(
            system_prompt=system_prompt,
            question=question,
            context=context,
            response_schema=response_schema,
            retries=1,
            temperature=0.0,
            max_tokens=400,
            mcp_server=state.get('mcp_server'),
        )

        review = result
        state['plan_ok'] = bool(review.get('ok', True))
        state['response_plan_review'] = review
        
        assessment = review.get('assessment', 'unknown')
        gaps = review.get('gaps', [])
        suggestions = review.get('suggestions', [])
        logger.info(f"PLAN_CRITIC: {assessment}, {len(gaps)} gaps, {len(suggestions)} suggestions")
        if gaps:
            logger.info(f"  Gaps: {', '.join(gaps[:2])}{'...' if len(gaps) > 2 else ''}")
        if suggestions:
            logger.info(f"  Suggestions: {', '.join(suggestions[:2])}{'...' if len(suggestions) > 2 else ''}")

        return ResponseHandler.handle_success(state, 'success')