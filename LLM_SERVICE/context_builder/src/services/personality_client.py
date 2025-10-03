from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter


class PersonalityClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    adapter: "VLLMAdapter"
    persona_name: str = 'Summarizer'

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            result: str = await self.adapter.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return result
            
        except Exception as ex:
            logger.error(f"LLM generation failed: {ex}")
            raise
