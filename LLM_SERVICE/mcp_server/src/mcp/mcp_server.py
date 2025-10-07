from __future__ import annotations

import asyncio
import threading

import colorama
from loguru import logger

from fastmcp import FastMCP

from src.adapters.rag_orchestrator_adapter import RagAdapter
from src.core.utils import EnvTools
from src.mcp.tools.rag_search_tool import RagSearchTool
from src.mcp.tools.health_check_tool import HealthCheckTool

from src.pydantic_schemas.mcp_server.models import (  # noqa: TC001
    RagSearchInput, RagSearchOutput, HealthOutput,
)


class McpServer:
    def __init__(self) -> None:
        self.fast_mcp = FastMCP("mcp_server")
        self.host: str = EnvTools.get_service_host('mcp_server')
        self.port: int = int(EnvTools.get_service_http_port('mcp_server'))
        self._is_running: bool = False
        self._thread: threading.Thread | None = None


    def register_tools(self) -> None:
        fast_mcp = self.fast_mcp

        @fast_mcp.tool(  # type: ignore[misc]
            name="rag.search",
            description="RAG search that returns digests with source chunks"
        )
        async def rag_search_tool(params: RagSearchInput) -> RagSearchOutput:
            rag_adapter = RagAdapter()
            rag_search_tool = RagSearchTool(rag_adapter)
            return await rag_search_tool.execute(params)

        @fast_mcp.tool(  # type: ignore[misc]
            name="health.check",
            description="Check health of RAG orchestrator",
        )
        async def health_check_tool() -> HealthOutput:
            rag_adapter = RagAdapter()
            health_check_tool = HealthCheckTool(rag_adapter)
            return await health_check_tool.execute()


    @property
    def is_running(self) -> bool:
        return self._is_running


    def _run_blocking(self) -> None:
        self.fast_mcp.run(transport="streamable-http", host=self.host, port=self.port)


    async def start(self) -> None:
        logger.info(
            f"{colorama.Fore.GREEN}MCP Server starting (HTTP transport){colorama.Style.RESET_ALL}"
        )

        self.register_tools()
        self._thread = threading.Thread(
            target=self._run_blocking, name="MCP", daemon=True
        )
        self._thread.start()
        self._is_running = True


    async def wait_terminated(self) -> None:
        while self._is_running:
            await asyncio.sleep(1)

