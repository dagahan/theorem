from __future__ import annotations

from src.rest.client.vllm_rest_client import VLLMRestClient
from src.rest.client.registry_rest_clients import RestClientRegistry
from src.domain.models import QuestionResponse


class VLLMAdapter:
    def __init__(self) -> None:
        self.client: VLLMRestClient = RestClientRegistry().register_client("vllm_talking", VLLMRestClient, timeout=60.0)


    async def generate_answer(
        self,
        question: str,
        system_prompt: str,
        context: str = "",
        stream: bool = False
    ) -> QuestionResponse:
        try:
            answer = await self.client.generate_answer(
                question=question,
                system_prompt=system_prompt,
                context=context,
                stream=stream
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




