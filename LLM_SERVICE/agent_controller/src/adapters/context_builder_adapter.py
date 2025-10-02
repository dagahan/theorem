from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.grpc.client.context_builder_grpc_client import ContextBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.domain.models import ContextBuilderRequest, ContextBuilderResponse


class ContextBuilderAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: ContextBuilderGrpcClient = registry.register_client(
            'context_builder',
            ContextBuilderGrpcClient,
        )


    async def build_context(
        self,
        request: ContextBuilderRequest
    ) -> ContextBuilderResponse:
        logger.info(f"Starting context building for {len(request.chunks)} chunks")
        try:
            response = await self.client.build_context(request)
            logger.info(
                "Context building completed: %s digests, success=%s",
                len(response.digests),
                response.success,
            )
            return response
        except Exception as e:
            logger.error(f"Context building failed: {e}")
            raise


    async def health_check(self) -> bool:
        return await self.client.health_check()

