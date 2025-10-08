from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loguru import logger

from src.core.retry import timeout_and_retry
from src.core.timeouts import TimeoutTools
from src.agents_graphs.graph_tools import GraphTools
from src.core.exceptions import NodeExecutionError

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState


class BaseNode(ABC):
    def __init__(self, timeout_key: str, default_timeout: float, max_attempts: int = 3) -> None:
        self._timeout_key = timeout_key
        self._default_timeout = default_timeout
        self._max_attempts = max_attempts


    @abstractmethod
    async def _execute_impl(
        self,
        graph_state: GraphState
    ) -> GraphState:
        pass


    @abstractmethod
    def _get_node_name(self) -> str:
        pass


    def _get_timeout_sec(self) -> float:
        return TimeoutTools.get_timeout(self._timeout_key, self._default_timeout)


    def _get_max_attempts(self) -> int:
        return self._max_attempts


    async def execute_node(
        self,
        graph_state: GraphState
    ) -> GraphState:
        started_at = time.time()
        
        try:
            result = await timeout_and_retry(
                max_attempts=self._get_max_attempts(),
                timeout_sec=self._get_timeout_sec()
            )(self._execute_impl)(graph_state)
            
            elapsed_ms = GraphTools.record_timing(graph_state, self._get_node_name(), started_at)

            self._log_success(graph_state, elapsed_ms)

            logger.info(f"{self._get_node_name()} completed in {elapsed_ms:.2f}ms")
            
            return result
            
        except Exception as ex:
            elapsed_ms = GraphTools.record_timing(graph_state, self._get_node_name(), started_at)
            
            self._log_error(graph_state, elapsed_ms, str(ex))

            logger.error(f"{self._get_node_name()} failed: {ex} in {elapsed_ms:.2f}ms")

            # Convert generic exception to NodeExecutionError for better error handling
            node_error = NodeExecutionError(
                node_name=self._get_node_name(),
                message=str(ex),
                details={"execution_time_ms": elapsed_ms, "original_error": str(ex)}
            )

            failed_state = GraphTools.mark_failure(graph_state, f"{self._get_node_name()} failed: {ex}")
            failed_state['success'] = False
            return failed_state


    def _log_success(
        self,
        graph_state: GraphState,
        elapsed_ms: float
    ) -> None:
        pass


    def _log_error(
        self,
        graph_state: GraphState,
        elapsed_ms: float,
        error: str
    ) -> None:
        pass