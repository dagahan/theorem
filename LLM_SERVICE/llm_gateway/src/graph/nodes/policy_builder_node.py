from __future__ import annotations
import time
from typing import TYPE_CHECKING
from loguru import logger

from src.graph.graph_utils import timeout_and_retry
from src.domain.models import PolicyRequest, PolicyHeader

if TYPE_CHECKING:
    from src.adapters.policy_builder_adapter import PolicyBuilderAdapter
    from src.domain.models import GraphState


class PolicyBuilderNode:
    def __init__(self, policy_builder_service: "PolicyBuilderAdapter") -> None:
        self.policy_builder_service = policy_builder_service


    @timeout_and_retry(max_attempts=3, timeout_sec=15.0)
    async def execute_node(self, graph_state: "GraphState") -> "GraphState":
        time_start_node = time.time()
        
        question = graph_state.get("original_question", "")
        query = graph_state.get("query")
        streaming = query.stream if query else False
        
        if not question:
            graph_state["policy_header"] = self._get_default_policy()
            graph_state["timings_ms"]["build_policy"] = (time.time() - time_start_node) * 1000
            return graph_state

        policy_request = PolicyRequest(
            question=question,
            question_type="general",
            difficulty="medium",
            streaming=streaming
        )

        result = await self.policy_builder_service.build_policy(policy_request)

        if not result.success:
            logger.warning(f"Policy building failed: {result.error}, using default policy")
            graph_state["policy_header"] = self._get_default_policy()
        else:
            graph_state["policy_header"] = PolicyHeader(policy_header=result.policy_header)

        elapsed = (time.time() - time_start_node) * 1000
        graph_state["timings_ms"]["build_policy"] = elapsed

        logger.info(f"Policy built: policy_header='{graph_state['policy_header'].policy_header[:50]}...'")

        return graph_state


    def _get_default_policy(self) -> PolicyHeader:
        return PolicyHeader(
            policy_header="Answer only with lawful, non-harmful, non-sexual, non-violent, and non-hate content; decline and do not facilitate wrongdoing or unsafe acts."
        )