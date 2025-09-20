from __future__ import annotations

from typing import TYPE_CHECKING

from src.grpc.client.context_builder_grpc_client import ContextBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.domain.models import ContextBuilderRequest, ContextBuilderResponse


class ContextBuilderAdapter:
    def __init__(self) -> None:
        self.client: ContextBuilderGrpcClient = GrpcClientRegistry().register_client("context_builder", ContextBuilderGrpcClient)


    async def build_context(
        self,
        request: ContextBuilderRequest
    ) -> ContextBuilderResponse:
        return await self.client.build_context(request)


    async def health_check(self) -> bool:
        return await self.client.health_check()



