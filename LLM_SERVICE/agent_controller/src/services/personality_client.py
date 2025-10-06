from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Type, Union

if TYPE_CHECKING:
    from pydantic import BaseModel
    from .llm_model import LLMModel


class PersonalityClient:
    def __init__(self, llm_model: "LLMModel") -> None:
        self.llm_model = llm_model


    async def generate(
        self,
        *,
        system_prompt: str,
        question: str,
        context: str,
        stream: bool,
        response_schema: Optional[Type[BaseModel]] = None,
        retries: int = 1,
        temperature: float,
        max_tokens: int
    ) -> Union[str, BaseModel]:

        if response_schema is None or stream:
            output_text = await self.llm_model.infer(
                system_prompt=system_prompt,
                question=question,
                context=context,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return output_text

        output_pydantic_model = await self.llm_model.pydantic_ai_request(
            system_prompt=system_prompt,
            question=question,
            context=context,
            response_schema=response_schema,
            retries=retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return output_pydantic_model


