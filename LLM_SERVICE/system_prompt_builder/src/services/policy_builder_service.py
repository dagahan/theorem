from __future__ import annotations

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from loguru import logger

from src.domain.models import (
    BuildSystemPromptResponse, HealthStatus
)
from src.adapters.policy_builder_adapter import PolicyBuilderAdapter


class SystemPromptBuilderService:
    def __init__(self) -> None:
        self.policy_adapter = PolicyBuilderAdapter()
        self.template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )


    async def get_health_status(self) -> HealthStatus:
        try:
            policy_status = "healthy" if await self.policy_adapter.health_check() else "unhealthy"

            return HealthStatus(
                status="healthy",
                policy_builder_status=policy_status
            )

        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return HealthStatus(
                status="unhealthy",
                policy_builder_status="unknown"
            )


    async def build_system_prompt(self) -> BuildSystemPromptResponse:
        try:
            policy_response = await self.policy_adapter.get_policy_header()
            
            if not policy_response.success:
                return BuildSystemPromptResponse(
                    system_prompt="",
                    success=False,
                    error=f"Policy building failed: {policy_response.error or 'unknown'}"
                )
                
            template = self.jinja_env.get_template("system_prompt.jinja")
            
            system_prompt = template.render(
                policy_header=policy_response.policy_header
            )

            return BuildSystemPromptResponse(
                system_prompt=system_prompt,
                success=True
            )

        except Exception as ex:
            logger.error(f"System prompt building failed: {ex}")
            return BuildSystemPromptResponse(
                system_prompt="",
                success=False,
                error=str(ex)
            )


