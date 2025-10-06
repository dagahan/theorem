from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.grpc.client.context_builder_grpc_client import ContextBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import ContextBuilderRequest, ContextBuilderResponse


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
                f"Context building completed: {len(response.digests)} digests, success={response.success}"
            )

            return response

        except Exception as ex:
            logger.error(f"Context building failed: {ex}")
            raise


    async def health_check(self) -> bool:
        return await self.client.health_check()

