from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from src.domain.models import GraphNodeFactory, StepSpec


AgentFactory = Callable[[GraphNodeFactory], list[StepSpec]]


class AgentGraphRegistry:
    _instance: AgentGraphRegistry | None = None
    _factories: dict[str, AgentFactory]

    def __new__(cls) -> AgentGraphRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._factories = {}
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


    def get(
        self,
        agent_name: str,
    ) -> AgentFactory:
        if agent_name not in self._factories:
            available = ', '.join(sorted(self._factories)) or '<none>'
            raise ValueError(f"Unknown agent '{agent_name}'. Registered agents: {available}")

        return self._factories[agent_name]


    def list_agents(self) -> list[str]:
        return sorted(self._factories)
