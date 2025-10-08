from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Type, Dict, Any

from pydantic_ai import Agent
from loguru import logger

from .pydantic_ai_model import PydanticAIBridgeModel
from .mcp_tools_formatter import MCPToolsFormatter

if TYPE_CHECKING:
    from pydantic import BaseModel
    from src.adapters.vllm_adapter import VLLMAdapter


class LLMModel:
    def __init__(self, *, vllm_adapter: "VLLMAdapter") -> None:
        self.vllm_adapter = vllm_adapter
        self.model_name = str(vllm_adapter.model_name)


    async def infer(
        self,
        *,
        system_prompt: str,
        question: str,
        context: str,
        stream: bool,
        temperature: float,
        max_tokens: int,
        mcp_server: Dict[str, Any] | None = None,
    ) -> str:
        if stream:
            raise RuntimeError("Stream isn't implemented yet.")

        mcp_tools_section = MCPToolsFormatter.format_tools_for_system_prompt(mcp_server or {})
        full_system_prompt = system_prompt + mcp_tools_section

        response = await self.vllm_adapter.generate_answer(
            question=question,
            system_prompt=full_system_prompt,
            context=context,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=None,
        )
        
        return response


    async def pydantic_ai_request(
        self,
        *,
        system_prompt: str,
        question: str,
        context: str,
        response_schema: Dict[str, Any],
        retries: int,
        temperature: float,
        max_tokens: int,
        mcp_server: Dict[str, Any] | None = None,
    ) -> Any:
        schema_format_contract = self._build_format_contract(response_schema)

        mcp_tools_section = MCPToolsFormatter.format_tools_for_system_prompt(mcp_server or {})

        full_system_prompt = f"{system_prompt}\n\n{mcp_tools_section}\n\n{schema_format_contract}"

        pydantic_ai_bridge_model = PydanticAIBridgeModel(
            vllm_adapter=self.vllm_adapter,
            model_name=self.model_name,
            system_prompt=full_system_prompt,
            context=context,
            question=question,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.debug(f"PYDANTIC AI TARGET SCHEMA: {response_schema}")
        
        agent = Agent(
            model=pydantic_ai_bridge_model,
            retries=retries
        )

        result = await agent.run(question)
        return json.loads(result.output)


    def _build_format_contract(
        self,
        schema: Dict[str, Any]
    ) -> str:
        return (
            "FORMAT CONTRACT\n"
            "Return ONLY a single JSON object that VALIDATES this JSON Schema (draft 2020-12).\n"
            "No prose, no code fences, no extra keys. If a required array has no items, return [].\n"
            f"SCHEMA:\n{json.dumps(schema, ensure_ascii=False)}\n"
            "OUTPUT: JSON only."
        )


