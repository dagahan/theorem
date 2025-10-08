from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Dict, List, Literal, Mapping, Optional

import httpx
from loguru import logger

from src.rest.client.base_rest_client import BaseRestClient


class MCPJsonRpcClient(BaseRestClient):
    def __init__(self, base_url: str, timeout: float = 30.0, 
                 transport: Literal["http", "streamable-http"] = "streamable-http") -> None:
        clean = base_url.rstrip("/")
        if clean.endswith("/mcp"):
            clean = clean[:-4]
        super().__init__(clean, timeout)
        self._session_id: Optional[str] = None
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self.transport = transport
        self._accept = "application/json" if self.transport == "http" else "application/json, text/event-stream"


    def _headers(self) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": self._accept,
        }
        if self._session_id:
            h["mcp-session-id"] = self._session_id
        return h

    def _extract_session_id(self, response: httpx.Response) -> None:
        for k, v in response.headers.items():
            if k.lower() == "mcp-session-id" and v:
                if self._session_id != v:
                    logger.debug(f"MCP: new session id received: {v}")
                self._session_id = v
                return


    async def _send_jsonrpc_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        try:
            response = await self.client.request(
                method="POST",
                url=f"{self.base_url}/mcp",
                json=payload,
                headers=self._headers(),
                timeout=self.client.timeout,
            )
            if response.status_code not in (200, 202):
                raise httpx.HTTPStatusError(f"Unexpected status for notification: {response.status_code}", request=response.request, response=response)
            self._extract_session_id(response)
        except Exception as ex:
            logger.error(f"Failed to send notification {method}: {ex}")
            raise


    async def _make_jsonrpc_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        *,
        require_session: bool = True,
        retried: bool = False,
    ) -> Dict[str, Any]:
        if request_id is None:
            request_id = str(uuid.uuid4())

        if require_session and not self._initialized:
            await self.initialize()

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        try:
            resp = await self.client.request(
                method="POST",
                url=f"{self.base_url}/mcp",
                json=payload,
                headers=self._headers(),
                timeout=self.client.timeout,
            )
            self._extract_session_id(resp)
            resp.raise_for_status()

            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                data = resp.json()
                if isinstance(data, dict) and "result" in data:
                    return data["result"]  # type: ignore[no-any-return]
                if isinstance(data, dict) and "error" in data:
                    raise RuntimeError(f"MCP JSON-RPC error: {data['error']}")
                return data  # type: ignore[no-any-return]

            if "text/event-stream" in ctype:
                return await self._parse_sse_response(resp)

            raise RuntimeError(f"Unsupported content-type from MCP: {ctype}")

        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (400, 406) and not retried:
                logger.warning(f"MCP {e.response.status_code}: will reinitialize session once")
                self._initialized = False
                self._session_id = None
                await self.initialize()
                return await self._make_jsonrpc_request(method, params, request_id, require_session=True, retried=True)
            raise


    async def _parse_sse_response(
        self,
        response: httpx.Response
    ) -> Dict[str, Any]:
        for line in response.text.splitlines():
            if line.startswith("data: "):
                txt = line[6:]

                try:
                    env = json.loads(txt)

                except json.JSONDecodeError:
                    continue

                if "error" in env:
                    raise RuntimeError(f"MCP JSON-RPC error: {env['error']}")

                if "result" in env:
                    return env["result"]  # type: ignore[no-any-return]

        raise RuntimeError("No valid SSE data JSON-RPC frame found")


    async def initialize(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return

            _ = await self._make_jsonrpc_request(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "agent_controller", "version": "1.0.0"},
                },
                require_session=False,
            )
            if not self._session_id:
                raise RuntimeError("MCP initialize: server did not return mcp-session-id header")

            await self._send_jsonrpc_notification("notifications/initialized")

            self._initialized = True
            logger.info(f"MCP session initialized: {self._session_id}")


    async def list_tools(self) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()

        result = await self._make_jsonrpc_request("tools/list", params={})
        if isinstance(result, dict) and isinstance(result.get("tools"), list):
            tools = result["tools"]
            logger.info(f"MCP: received {len(tools)} tools")
            return tools  # type: ignore[no-any-return]

        if isinstance(result, list):
            logger.info(f"MCP: received {len(result)} tools")
            return result

        logger.warning(f"MCP: unexpected tools response: {type(result)}")
        return []
        

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()

        args = dict(arguments or {})
        logger.info(f"Calling MCP tool '{name}' with args: {list(args.keys())}")

        result = await self._make_jsonrpc_request(
            method="tools/call",
            params={"name": name, "arguments": {"params": args}}
        )

        return result if isinstance(result, dict) else {"result": result}


    async def close(self) -> None:
        await super().close()
        self._initialized = False
        self._session_id = None


