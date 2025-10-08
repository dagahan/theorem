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


class ResponsePlannerNode(BaseNode):
    def __init__(self, vllm_adapter: "VLLMAdapter") -> None:
        super().__init__('RESPONSE_PLANNER_NODE_TIMEOUT_SEC', 15.0, 2)
        self.llm = LLMModel(vllm_adapter=vllm_adapter)


    def _get_node_name(self) -> str:
        return 'resp_plan'


    async def _execute_impl(self, state: "GraphState") -> "GraphState":
        personalities = state.get('personalities')
        if not personalities or 'response_planner' not in personalities.personalities:
            return ResponseHandler.handle_failure(state, "response_planner personality is missing")

        persona = personalities.personalities['response_planner']
        system_prompt = persona.system_prompt

        response_schema = persona.response_schema
        if not response_schema or not isinstance(response_schema, dict):
            return ResponseHandler.handle_failure(state, "response_planner response schema missing or invalid")

        question = state.get('question', '')
        context = json.dumps({
            "context_digests": [
                {"title": d.title, "summary": d.summary} 
                for d in state.get('context_digests', [])
            ],
            "cycle_summary": state.get('cycle_summary', {}),
        }, ensure_ascii=False)

        result = await self.llm.pydantic_ai_request(
            system_prompt=system_prompt,
            question=question,
            context=context,
            response_schema=response_schema,
            retries=1,
            temperature=0.0,
            max_tokens=800,
            mcp_server=state.get('mcp_server'),
        )

        plan_data = result
        state['response_plan'] = plan_data
        
        sections = plan_data.get('sections', [])
        citations = plan_data.get('citations', [])
        logger.info(f"RESPONSE_PLANNER: Created {len(sections)} sections, {len(citations)} citations")
        for i, section in enumerate(sections[:3], 1):  # Show first 3 sections
            title = section.get('title', 'Untitled')
            bullets = len(section.get('bullets', []))
            logger.info(f"  Section {i}: {title} ({bullets} bullets)")

        return ResponseHandler.handle_success(state, 'success')