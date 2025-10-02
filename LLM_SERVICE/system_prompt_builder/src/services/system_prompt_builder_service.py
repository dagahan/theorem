from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger

from src.adapters.policy_builder_adapter import PolicyBuilderAdapter
from src.domain.models import BuildSystemPromptRequest, BuildSystemPromptResponse, HealthStatus, PersonaPrompt


class SystemPromptBuilderService:
    def __init__(self) -> None:
        self.policy_adapter = PolicyBuilderAdapter()
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def get_health_status(self) -> HealthStatus:
        try:
            policy_status = "healthy" if await self.policy_adapter.health_check() else "unhealthy"
            return HealthStatus(
                status="healthy",
                policy_builder_status=policy_status
            )

        except Exception as ex:  # noqa: BLE001
            logger.error("Health check failed: %s", ex)
            return HealthStatus(
                status="unhealthy",
                policy_builder_status="unknown"
            )


    async def build_persona_system_prompt(
        self,
        request: BuildSystemPromptRequest,
    ) -> BuildSystemPromptResponse:
        try:
            policy_header_response = await self.policy_adapter.get_policy_header()

            if not policy_header_response.success:
                error = policy_header_response.error or 'policy header unavailable'
                return BuildSystemPromptResponse(
                    personalities=[],
                    success=False,
                    error=error
                )

            policy_header = policy_header_response.policy_header

            personalities: list[PersonaPrompt] = []

            for persona in request.persona_names:
                template = self.jinja_env.get_template(self._template_name(persona))

                prompt = template.render(policy_header=policy_header).strip()

                personalities.append(PersonaPrompt(
                    name=persona,
                    prompt=prompt
                ))

            return BuildSystemPromptResponse(
                personalities=personalities,
                success=True
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("System prompt building failed: %s", exc)
            return BuildSystemPromptResponse(personalities=[], success=False, error=str(exc))


    @staticmethod
    def _template_name(persona: str) -> str:
        return f"{persona.lower()}_prompt.jinja"



