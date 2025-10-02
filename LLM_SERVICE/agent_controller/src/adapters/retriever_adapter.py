from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.grpc.client.retriever_grpc_client import RetrieverGrpcClient

if TYPE_CHECKING:
    from protobuf_stubs import retriever_pb2
    from src.domain.models import RetrieveRequest, RetrieveResponse


class RetrieverAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: RetrieverGrpcClient = registry.register_client(
            'retriever',
            RetrieverGrpcClient,
        )


    async def retrieve_context(
        self,
        request: RetrieveRequest
    ) -> RetrieveResponse:
        logger.info(f"Starting context retrieval for query: '{request.question}'")
        try:
            response = await self.client.retrieve_context(request)
            logger.info(f"Context retrieval completed: {len(response.results)} chunks")
            return response
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            raise


    async def health_check(self) -> retriever_pb2.HealthResponse:
        return await self.client.health_check()
