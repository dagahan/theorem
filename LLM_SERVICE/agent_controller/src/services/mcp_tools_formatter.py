from __future__ import annotations

import json
from typing import Any, Dict


class MCPToolsFormatter:
    @staticmethod
    def format_tools_for_system_prompt(mcp_server: Dict[str, Any]) -> str:
        if not mcp_server or not isinstance(mcp_server, dict):
            return ""
        
        catalog = mcp_server.get("catalog", {})
        tools = catalog.get("tools", {})
        
        if not tools:
            return ""
        
        tools_descriptions = []
        for tool_name, tool_meta in tools.items():
            if not isinstance(tool_meta, dict):
                continue
                
            description = tool_meta.get("description", "No description available")
            input_schema = tool_meta.get("input_schema", {})
            
            tool_info = f"- {tool_name}: {description}"
            
            if input_schema and isinstance(input_schema, dict):
                properties = input_schema.get("properties", {})
                if properties:
                    params = []
                    for param_name, param_schema in properties.items():
                        param_type = param_schema.get("type", "string")
                        param_desc = param_schema.get("description", "")
                        if param_desc:
                            params.append(f"  - {param_name} ({param_type}): {param_desc}")
                        else:
                            params.append(f"  - {param_name} ({param_type})")
                    
                    if params:
                        tool_info += "\n  Parameters:\n" + "\n".join(params)
            
            tools_descriptions.append(tool_info)
        
        if not tools_descriptions:
            return ""
        
        return (
            "\n\nAVAILABLE TOOLS:\n"
            "You have access to the following MCP tools:\n\n"
            + "\n\n".join(tools_descriptions) +
            "\n\nUse these tools when planning and executing actions. "
            "Each tool has specific parameters that must be provided correctly."
        )


    @staticmethod
    def get_tools_list(mcp_server: Dict[str, Any]) -> list[str]:
        if not mcp_server or not isinstance(mcp_server, dict):
            return []
        
        catalog = mcp_server.get("catalog", {})
        tools = catalog.get("tools", {})
        
        return list(tools.keys()) if isinstance(tools, dict) else []


    @staticmethod
    def get_tool_schema(mcp_server: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        if not mcp_server or not isinstance(mcp_server, dict):
            return {}
        
        catalog = mcp_server.get("catalog", {})
        tools = catalog.get("tools", {})
        
        if not isinstance(tools, dict):
            return {}
        
        tool_meta = tools.get(tool_name, {})
        if not isinstance(tool_meta, dict):
            return {}
        
        return tool_meta.get("input_schema", {})  # type: ignore[no-any-return]