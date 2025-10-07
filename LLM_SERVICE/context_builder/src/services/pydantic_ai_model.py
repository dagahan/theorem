from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic_ai.models import ModelResponse, Model
from pydantic_ai.messages import TextPart

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter


class PydanticAIBridgeModel(Model):  # type: ignore
    def __init__(
        self,
        *,
        adapter: "VLLMAdapter",
        model_name: str,
        system_prompt: str,
        context: str,
        question: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> None:
        self.adapter = adapter
        self.model_name_str = model_name
        self.system_prompt = system_prompt
        self.context = context
        self.question = question
        self.temperature = temperature
        self.max_tokens = max_tokens


    @property
    def model_name(self) -> str:
        return self.model_name_str


    @property
    def system(self) -> str:
        return "llm_model_bridge"


    async def request(
        self,
        _messages: list[Any],
        _model_settings: Any,
        _model_request_parameters: Any,
    ) -> ModelResponse:

        text = await self.adapter.complete(
            system_prompt=self.system_prompt,
            context=self.context,
            question=self.question,
            temperature=self.temperature or 0.7,
            max_tokens=self.max_tokens or 1000,
            stream=False,
        )

        return ModelResponse(
            parts=[TextPart(content=(text or "").strip())],
            model_name=self.model_name_str
        )


        