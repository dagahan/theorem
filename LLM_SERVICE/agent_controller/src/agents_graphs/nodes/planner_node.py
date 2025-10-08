from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.core.handlers import ResponseHandler
from src.services.llm_model import LLMModel
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.vllm_adapter import VLLMAdapter


class PlannerNode(BaseNode):
    def __init__(self, vllm_adapter: "VLLMAdapter") -> None:
        super().__init__('PLANNER_NODE_TIMEOUT_SEC', 15.0, 2)
        self.llm = LLMModel(vllm_adapter=vllm_adapter)


    def _get_node_name(self) -> str:
        return 'plan'


    async def _execute_impl(self, state: "GraphState") -> "GraphState":
        personalities = state.get('personalities')
        if not personalities or 'planner' not in personalities.personalities:
            return ResponseHandler.handle_failure(state, "planner personality is missing")

        persona = personalities.personalities['planner']
        system_prompt = persona.system_prompt

        response_schema = persona.response_schema
        if not response_schema or not isinstance(response_schema, dict):
            return ResponseHandler.handle_failure(state, "planner response schema missing or invalid")

        question = state.get('question', '')
        cycle_summary = state.get('cycle_summary', {})
        
        previous_plans = state.get('previous_plans', [])
        current_iter = state.get('cot', {}).get('iter', 0)
        
        is_plan_repeated = False
        if len(previous_plans) > 0:
            last_plan = previous_plans[-1]
            last_actions = last_plan.get('actions', [])
            if len(last_actions) > 0:
                last_query = last_actions[0].get('args', {}).get('query', '')
                if last_query and current_iter > 0:
                    is_plan_repeated = True
        
        context_payload = {
            "cycle_summary": cycle_summary,
            "previous_plans": previous_plans[-2:] if len(previous_plans) > 0 else [],
            "current_iteration": current_iter,
            "is_plan_repeated": is_plan_repeated,
        }
        context = json.dumps(context_payload, ensure_ascii=False)

        result = await self.llm.pydantic_ai_request(
            system_prompt=system_prompt,
            question=question,
            context=context,
            response_schema=response_schema,
            retries=3,
            temperature=0.0,
            max_tokens=800,
            mcp_server=state.get('mcp_server'),
        )

        plan_data = result
        state['plan'] = plan_data
        
        previous_plans = state.get('previous_plans', [])
        previous_plans.append({
            "iteration": current_iter,
            "subgoals": plan_data.get('subgoals', []),
            "actions": plan_data.get('actions', []),
        })
        state['previous_plans'] = previous_plans[-5:]

        subgoals = plan_data.get('subgoals', [])
        actions = plan_data.get('actions', [])
        
        logger.info(f"PLANNER: Created {len(subgoals)} goals, {len(actions)} actions")
        logger.info(f"PLANNER: Full plan data: {plan_data}")
        for i, goal in enumerate(subgoals, 1):
            logger.info(f"  Goal {i}: {goal.get('id', 'unknown')} - {goal.get('need', 'no description')}")
        for i, action in enumerate(actions, 1):
            tool = action.get('tool', 'unknown')
            args = action.get('args', {})
            logger.info(f"  Action {i}: {tool} - {args.get('query', 'no query')}")

        return ResponseHandler.handle_success(state, 'success')