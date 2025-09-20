from __future__ import annotations

from typing import TYPE_CHECKING

from src.grpc.client.system_prompt_builder_grpc_client import SystemPromptBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.domain.models import SystemPromptResponse


class SystemPromptBuilderAdapter:
    def __init__(self) -> None:
        self.client: SystemPromptBuilderGrpcClient = GrpcClientRegistry().register_client("system_prompt_builder", SystemPromptBuilderGrpcClient)


    async def build_system_prompt(self) -> SystemPromptResponse:
        return await self.client.build_system_prompt()


    async def health_check(self) -> bool:
        return await self.client.health_check()


