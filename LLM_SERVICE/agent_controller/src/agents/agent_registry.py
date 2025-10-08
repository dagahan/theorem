from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import StateGraph
from loguru import logger

from src.pydantic_schemas.agent_controller import StepSpec
from src.agents_graphs.graph_node_factory import GraphNodeFactory


AgentFactory = Callable[[GraphNodeFactory], list[StepSpec]]
CoTGraphFactory = Callable[[GraphNodeFactory], StateGraph]


class AgentGraphRegistry:
    _instance: AgentGraphRegistry | None = None
    _factories: dict[str, AgentFactory]
    _cot_factories: dict[str, CoTGraphFactory]


    def __new__(cls) -> AgentGraphRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories = {}
            cls._instance._cot_factories = {}
        return cls._instance


    def register(
        self,
        agent_name: str,
        factory: AgentFactory,
    ) -> None:
        if agent_name in self._factories:
            logger.warning(f"Agent '{agent_name}' is already registered. Overwriting definition.")

        self._factories[agent_name] = factory
        logger.debug(f"Registered agent graph: {agent_name}")


    def register_cot(
        self,
        agent_name: str,
        factory: CoTGraphFactory,
    ) -> None:
        if agent_name in self._cot_factories:
            logger.warning(f"CoT agent '{agent_name}' is already registered. Overwriting definition.")

        self._cot_factories[agent_name] = factory
        logger.debug(f"Registered CoT agent graph: {agent_name}")


    def get(
        self,
        agent_name: str,
    ) -> AgentFactory:
        if agent_name not in self._factories:
            available = ', '.join(sorted(self._factories)) or '<none>'
            raise ValueError(f"Unknown agent '{agent_name}'. Registered agents: {available}")

        return self._factories[agent_name]


    def get_cot(
        self,
        agent_name: str,
    ) -> CoTGraphFactory:
        if agent_name not in self._cot_factories:
            available = ', '.join(sorted(self._cot_factories)) or '<none>'
            raise ValueError(f"Unknown CoT agent '{agent_name}'. Registered CoT agents: {available}")

        return self._cot_factories[agent_name]


    def has_cot(self, agent_name: str) -> bool:
        return agent_name in self._cot_factories


    def list_agents(self) -> list[str]:
        return sorted(self._factories)


    def list_cot_agents(self) -> list[str]:
        return sorted(self._cot_factories)


