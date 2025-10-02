from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.grpc.client.system_prompt_builder_grpc_client import SystemPromptBuilderGrpcClient

if TYPE_CHECKING:
    from src.domain.models import SystemPromptResponse


class SystemPromptBuilderAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: SystemPromptBuilderGrpcClient = registry.register_client(
            'system_prompt_builder',
            SystemPromptBuilderGrpcClient,
        )


    async def build_system_prompt(
        self,
        persona_names: list[str],
    ) -> SystemPromptResponse:
        logger.info(f"Starting system prompt building for personas: {persona_names}")
        try:
            response = await self.client.build_system_prompt(persona_names)
            logger.info(
                "System prompt building completed: %s personas, success=%s",
                len(response.personalities),
                response.success,
            )
            return response
        except Exception as e:
            logger.error(f"System prompt building failed: {e}")
            raise


    async def health_check(self) -> bool:
        return await self.client.health_check()


