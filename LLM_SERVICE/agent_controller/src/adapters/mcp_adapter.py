from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, Mapping

from loguru import logger

from src.core.timeouts import TimeoutTools
from src.core.utils import EnvTools
from src.pydantic_schemas.mcp_server.models import (
    RagSearchInput, RagSearchOutput, HealthOutput,
)

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
from src.rest.client.registry_rest_clients import RestClientRegistry
from src.rest.client.mcp_jsonrpc_client import MCPJsonRpcClient


class MCPAdapter:
    def __init__(self) -> None:
        registry = RestClientRegistry()
        timeout = TimeoutTools.get_timeout("MCP_HTTP_TIMEOUT_SEC", 30.0)
        self.client: MCPJsonRpcClient = registry.register_client("mcp_server", MCPJsonRpcClient, timeout=timeout, transport="streamable-http")

        ttl_raw = EnvTools.load_env_var("MCP_CATALOG_TTL_SEC")
        try:
            self._catalog_ttl = int(ttl_raw) if ttl_raw else 600

        except Exception:
            self._catalog_ttl = 600


    async def ensure_catalog_in_state(
        self,
        state: "GraphState"
    ) -> None:
        mcp_state = state.get("mcp_server") or {}
        catalog = mcp_state.get("catalog") or {}
        fetched_at = float(catalog.get("fetched_at") or 0.0)
        now = time.time()

        if now - fetched_at < float(catalog.get("ttl_sec") or self._catalog_ttl) and catalog.get("tools"):
            return

        tools_payload = await self.client.list_tools()

        tools_by_name: Dict[str, Any] = {}

        if isinstance(tools_payload, list):
            for item in tools_payload:
                name = item.get("name")

                if isinstance(name, str) and name:
                    tools_by_name[name] = item

        elif isinstance(tools_payload, dict):
            for name, meta in tools_payload.items():
                tools_by_name[str(name)] = meta

        else:
            tools_by_name = {}

        compiled: Dict[str, Dict[str, Any]] = {}
        for name, meta in tools_by_name.items():
            input_schema = meta.get("input_schema")
            output_schema = meta.get("output_schema")

            try:
                compiled[name] = {
                    "input_schema": input_schema,
                    "output_schema": output_schema,
                }

            except Exception as ex:
                logger.warning(f"MCP: failed to compile schemas for '{name}': {ex}")
                compiled[name] = {"input_model": None, "output_model": None}

        state["mcp_server"] = {
            "endpoint": self.client.base_url,
            "catalog": {"tools": tools_by_name, "fetched_at": now, "ttl_sec": self._catalog_ttl},
            "compiled": compiled,
        }

        logger.info(f"MCP: catalog stored in graph_state with {len(tools_by_name)} tools")


    def _extract_json_payload(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        content = raw.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "json" and isinstance(item.get("json"), dict):
                        return item["json"]  # type: ignore[no-any-return]
                    if item.get("type") == "text" and isinstance(item.get("text"), str):
                        # возможно сырой JSON строкой — попробуем распарсить
                        import json
                        txt = item["text"].strip()
                        try:
                            return json.loads(txt)  # type: ignore[no-any-return]
                        except Exception:
                            pass
        return None

    async def rag_search(self, params: RagSearchInput) -> RagSearchOutput:
        raw = await self.client.call_tool("rag.search", params.model_dump())
        
        if isinstance(raw, dict) and raw.get("isError") is True:
            content = raw.get("content", [])
            error_msg = "Unknown MCP error"
            if content and isinstance(content, list) and len(content) > 0:
                first_content = content[0]
                if isinstance(first_content, dict) and "text" in first_content:
                    error_msg = first_content["text"]
            
            logger.error(f"MCP tool returned error: {error_msg}")
            return RagSearchOutput(digests=[])
        
        payload = self._extract_json_payload(raw) or {}
        try:
            return RagSearchOutput.model_validate(payload)  # type: ignore[no-any-return]
        except Exception:
            logger.warning(f"Unexpected MCP response structure: {raw}")
            return RagSearchOutput(digests=[])


    async def health_check(self) -> HealthOutput:
        raw = await self.client.call_tool("health.check", {})
        
        payload = self._extract_json_payload(raw) or {}
        try:
            return HealthOutput.model_validate(payload)  # type: ignore[no-any-return]
        except Exception:
            logger.warning(f"Unexpected MCP health response structure: {raw}")
            return HealthOutput(status="degraded", rag_orchestrator="error")


    async def call_tool(
        self,
        state: Mapping[str, Any],
        tool_name: str,
        args: Mapping[str, Any] | None = None
    ) -> Dict[str, Any]:
        compiled = (state.get("mcp_server") or {}).get("compiled") or {}
        entry = compiled.get(tool_name) or {}
        input_model = entry.get("input_model")
        output_model = entry.get("output_model")

        payload = dict(args or {})
        
        if input_model is not None:
            payload = input_model(**payload).model_dump()

        result = await self.client.call_tool(tool_name, payload)

        if output_model is not None:
            return output_model(**result).model_dump()  # type: ignore[no-any-return]

        return result



