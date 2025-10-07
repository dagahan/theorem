from __future__ import annotations

from typing import TYPE_CHECKING

from src.pydantic_schemas.mcp_server.models import HealthOutput

if TYPE_CHECKING:
    from src.adapters.rag_orchestrator_adapter import RagAdapter


class HealthCheckTool:
    def __init__(self, rag_adapter: RagAdapter) -> None:
        self.rag_adapter = rag_adapter


    async def execute(self) -> HealthOutput:
        ok = await self.rag_adapter.health_check()
        return HealthOutput(
            status="ok" if ok else "degraded",
            rag_orchestrator="ok" if ok else "error"
        )


