from __future__ import annotations

from src.domain.models import QuestionResponse
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
        context: str = "",
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> QuestionResponse:
        try:
            answer = await self.client.generate_answer(
                question=question,
                system_prompt=system_prompt,
                context=context,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return QuestionResponse(
                answer=answer,
                success=True
            )
            
        except Exception as ex:
            return QuestionResponse(
                answer="",
                success=False,
                error=str(ex)
            )


    async def health_check(self) -> bool:
        return await self.client.health_check()


    async def complete(
        self,
        *,
        system_prompt: str,
        context: str,
        question: str,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> str:
        return await self.client.generate_answer(
            question=question,
            system_prompt=system_prompt,
            context=context,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
        )


