from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.core.handlers import ResponseHandler
from src.agents_graphs.nodes.base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.mcp_adapter import MCPAdapter


class MCPInitNode(BaseNode):
    def __init__(self, mcp_adapter: "MCPAdapter") -> None:
        super().__init__("MCP_INIT_TIMEOUT_SEC", 30.0, 2)
        self.mcp_adapter = mcp_adapter


    def _get_node_name(self) -> str:
        return "mcp_init"


    async def _execute_impl(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        logger.info("MCP_INIT: Initializing MCP session and loading tools catalog")
        
        try:
            await self.mcp_adapter.ensure_catalog_in_state(graph_state)
            
            mcp_server_data = graph_state.get("mcp_server", {})
            if not isinstance(mcp_server_data, dict):
                mcp_server_data = {}
            tools_count = len(mcp_server_data.get("catalog", {}).get("tools", {}))
            
            logger.info(f"MCP_INIT: Successfully loaded {tools_count} tools")
            
            tools_catalog = mcp_server_data.get("catalog", {}).get("tools", {})
            
            logger.info(f"MCP_INIT: Available tools: {list(tools_catalog.keys())}")
            for tool_name, tool_meta in tools_catalog.items():
                logger.info(f"MCP_INIT: Tool '{tool_name}': {tool_meta}")
            
            graph_state["mcp_server"] = mcp_server_data
            
            return ResponseHandler.handle_success(graph_state, "MCP tools catalog loaded")
            
        except Exception as ex:
            logger.error(f"MCP_INIT: Failed to initialize MCP session: {ex}")
            return ResponseHandler.handle_failure(
                graph_state, 
                f"MCP initialization failed: {ex}"
            )


            