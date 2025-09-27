from __future__ import annotations

from src.rest.client.vllm_rest_client import VLLMRestClient
from src.rest.client.registry_rest_clients import RestClientRegistry


class VLLMAdapter:
    def __init__(self) -> None:
        self.client: VLLMRestClient = RestClientRegistry().register_client("vllm_talking", VLLMRestClient)


    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.2
    ) -> str:
        return await self.client.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )


    async def health_check(self) -> bool:
        return await self.client.health_check()

