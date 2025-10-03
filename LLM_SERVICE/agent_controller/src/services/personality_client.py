from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent
from pydantic_ai.messages import TextPart
from pydantic_ai.models import Model, ModelResponse

from src.pydantic_schemas.agent_controller import QuestionResponse, ResponderConfig, ResponderRuntime

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter


class ResponderPayload(BaseModel):  # type: ignore[misc]
    answer: str


class _ResponderModel(Model):  # type: ignore[misc]
    def __init__(
        self,
        *,
        config: ResponderConfig,
        adapter: VLLMAdapter,
        runtime: ResponderRuntime,
    ) -> None:
        self._config = config
        self._adapter = adapter
        self._runtime = runtime

    @property
    def model_name(self) -> str:
        return self._config.model_name

    @property
    def system(self) -> str:
        return 'responder'

    async def request(
        self,
        _messages: list[Any],
        _model_settings: Any,
        _model_request_parameters: Any,
    ) -> ModelResponse:
        response_text = await self._adapter.complete(
            system_prompt=self._runtime.system_prompt,
            context=self._runtime.context,
            question=self._runtime.question,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            stream=self._runtime.stream,
        )

        return ModelResponse(
            parts=[TextPart(content=response_text.strip())],
            model_name=self._config.model_name,
        )


class PersonalityClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    vllm_adapter: VLLMAdapter
    config: ResponderConfig | None = None

    async def generate(
        self,
        *,
        personality_name: str,
        personality_prompts: dict[str, str],
        question: str,
        context: str,
        stream: bool,
        agent_name: str,
    ) -> QuestionResponse:
        system_prompt = personality_prompts.get(personality_name)
        if not system_prompt:
            raise ValueError(f"missing system prompt for personality '{personality_name}'")

        responder_config = self.config or ResponderConfig(model_name=self.vllm_adapter.model_name)
        runtime = ResponderRuntime(
            system_prompt=self._enrich_system_prompt(system_prompt, agent_name),
            question=question,
            context=context,
            agent_name=agent_name,
            stream=stream,
        )

        model = _ResponderModel(
            config=responder_config,
            adapter=self.vllm_adapter,
            runtime=runtime,
        )

        agent = Agent(
            model=model,
            output_type=ResponderPayload,
            retries=1,
        )

        try:
            result = await agent.run(user_prompt='')
            answer = result.output.answer.strip()
            return self._build_success_response(answer)

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Responder generation failed: {exc}")
            return self._build_error_response(str(exc))

    @staticmethod
    def _enrich_system_prompt(system_prompt: str, agent_name: str) -> str:
        agent_marker = f"\n\nAgent identifier: {agent_name.strip()}"
        return f"{system_prompt.strip()}{agent_marker}"

    @staticmethod
    def _build_success_response(answer: str) -> QuestionResponse:
        return QuestionResponse(
            answer=answer,
            success=True,
        )

    @staticmethod
    def _build_error_response(error: str) -> QuestionResponse:
        return QuestionResponse(
            answer='',
            success=False,
            error=error,
        )
