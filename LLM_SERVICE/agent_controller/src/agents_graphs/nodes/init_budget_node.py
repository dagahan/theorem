from __future__ import annotations

import time
from typing import TYPE_CHECKING

from loguru import logger

from src.core.utils import EnvTools
from src.core.handlers import ResponseHandler
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState


class InitBudgetNode(BaseNode):
    def __init__(self) -> None:
        super().__init__('INIT_BUDGET_NODE_TIMEOUT_SEC', 2.0, 1)


    def _get_node_name(self) -> str:
        return 'init_budgets'


    async def _execute_impl(self, state: "GraphState") -> "GraphState":
        max_iters = int(EnvTools.load_env_var('COT_MAX_ITERS') or 6)
        deadline_ms = float(EnvTools.load_env_var('COT_DEADLINE_MS') or 7000.0)
        token_budget = int(EnvTools.load_env_var('COT_TOKEN_BUDGET') or 3000)

        now_ms = time.time() * 1000.0
        
        state['cot'] = {
            'iter': 0,
        }
        
        state['budgets'] = {
            'tokens_left': token_budget,
            'deadline_at_ms': now_ms + deadline_ms,
            'max_iters': max_iters,
        }
        
        state.setdefault('evidence', {})
        state['evidence'].setdefault('claims', [])
        state.setdefault('cycle_summary', {})
        state.setdefault('previous_plans', [])

        logger.info(f"INIT_BUDGET: {max_iters} max_iters, {deadline_ms}ms deadline, {token_budget} tokens")

        return ResponseHandler.handle_success(state, 'success')