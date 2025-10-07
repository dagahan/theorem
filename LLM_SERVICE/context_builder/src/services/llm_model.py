from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type

from pydantic_ai import Agent

from src.services.pydantic_ai_model import PydanticAIBridgeModel

if TYPE_CHECKING:
    from pydantic import BaseModel
    from src.adapters.vllm_adapter import VLLMAdapter


class LLMModel:
    def __init__(self, *, adapter: "VLLMAdapter") -> None:
        self.adapter = adapter
        self.model_name = str(adapter.model_name)


    async def infer(
        self,
        *,
        system_prompt: str,
        question: str,
        context: str,
        stream: bool,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if stream:
            raise RuntimeError("Stream isn't implemented yet.")

        output = await self.adapter.complete(
            system_prompt=system_prompt,
            context=context,
            question=question,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            response_format=response_format,
        )

        return str(output)


    async def pydantic_ai_request(
        self,
        *,
        system_prompt: str,
        question: str,
        context: str,
        response_schema: Type[BaseModel],
        retries: int = 1,
        temperature: float,
        max_tokens: int,
    ) -> BaseModel:

        pydantic_ai_bridge_model = PydanticAIBridgeModel(
            adapter=self.adapter,
            model_name=self.model_name,
            system_prompt=system_prompt,
            context=context,
            question=question,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        agent = Agent(
            model=pydantic_ai_bridge_model,
            output_type=response_schema,
            retries=retries
        )

        result = await agent.run()

        return result.output



