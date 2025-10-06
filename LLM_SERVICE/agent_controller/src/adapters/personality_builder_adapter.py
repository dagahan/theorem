from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.grpc.client.personality_builder_grpc_client import PersonalityBuilderGrpcClient

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import PersonalityResponse


class PersonalityBuilderAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: PersonalityBuilderGrpcClient = registry.register_client(
            'personality_builder',
            PersonalityBuilderGrpcClient,
        )


    async def build_personalities(
        self,
        persona_names: list[str],
        agent_name: str = "",
    ) -> PersonalityResponse:
        logger.info(f"Starting personality building for personas: {persona_names}, agent: {agent_name}")
        try:
            response = await self.client.build_personalities(persona_names, agent_name)
            logger.info(
                f"Personality building completed: {len(response.personalities)} personalities, success={response.success}"
            )

            return response

        except Exception as ex:
            logger.error(f"Personality building failed: {ex}")
            raise


    async def health_check(self) -> bool:
        return await self.client.health_check()


