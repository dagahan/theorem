from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Iterable
from loguru import logger

from pydantic_ai.models import Model, ModelResponse
from pydantic_ai.messages import TextPart

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter


class PydanticAIBridgeModel(Model):  # type: ignore
    def __init__(
        self,
        *,
        vllm_adapter: "VLLMAdapter",
        model_name: str,
        system_prompt: str,
        context: str,
        question: str,
        temperature: float,
        max_tokens: int
    ) -> None:
        self.vllm_adapter = vllm_adapter
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
        return "bridge"


    def _sanitize_user_text(self, text: str) -> str:
        banned = "Plain text responses are not permitted"
        return text.replace(banned, "").strip()


    async def request(
        self,
        _messages: list[Any],
        _model_settings: Any,
        _model_request_parameters: Any
    ) -> ModelResponse:
        system_text, body_text = self._split(_messages)
        
        sanitized_question = self._sanitize_user_text(body_text)
        sanitized_context = self._sanitize_user_text(self.context or "")

        base_system = self._join([self.system_prompt, system_text])
        
        response = await self.vllm_adapter.generate_answer(
            question=sanitized_question,
            system_prompt=base_system,
            context=sanitized_context,
            stream=False,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        
        response_text = response.strip() if response else ""
        logger.debug(f"Bridge: {len(response_text)} chars.\n{response_text}")

        return ModelResponse(
            parts=[TextPart(content=response_text)],
            model_name=self.model_name_str
        )


    @staticmethod
    def _split(messages: Iterable[Any]) -> tuple[str, str]:
        system_parts: list[str] = []
        body_parts: list[str] = []

        for msg in messages or []:
            if hasattr(msg, 'parts'):
                for part in msg.parts:
                    if hasattr(part, 'content'):
                        content = part.content.strip()

                        if content:
                            if hasattr(part, 'type') and part.type == "system":
                                system_parts.append(content)

                            else:
                                body_parts.append(content)
                                
            elif hasattr(msg, 'get'):
                role = str(msg.get("role", "")).lower()
                for part in msg.get("parts") or []:
                    if isinstance(part, dict) and part.get("type") == "text":
                        content = (part.get("content") or "").strip()
                        if content:
                            (system_parts if role == "system" else body_parts).append(content)

        return ("\n\n".join(system_parts), "\n\n".join(body_parts))


    @staticmethod
    def _join(texts: list[str]) -> str:
        return "\n\n".join(t for t in texts if t.strip())