from __future__ import annotations

from typing import Dict

from src.rest.client.registry_rest_clients import RestClientRegistry
from src.rest.client.vllm_rest_client import VLLMRestClient


class VLLMAdapter:
    def __init__(self) -> None:
        registry = RestClientRegistry()
        self.client: VLLMRestClient = registry.register_client(
            'vllm_talking',
            VLLMRestClient,
            timeout=60.0,
        )

    @property
    def model_name(self) -> str:
        return self.client.model_name


    async def generate_answer(
        self,
        question: str,
        system_prompt: str,
        context: str,
        stream: bool,
        temperature: float,
        max_tokens: int,
        response_format: Dict[str, str] | None,
    ) -> str:
        try:
            answer = await self.client.generate_answer(
                question=question,
                system_prompt=system_prompt,
                context=context,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            
            return answer
            
        except Exception as ex:
            return ""


    async def health_check(self) -> bool:
        return await self.client.health_check()




