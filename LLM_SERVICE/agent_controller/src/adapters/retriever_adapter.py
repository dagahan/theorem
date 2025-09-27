
from __future__ import annotations

from typing import TYPE_CHECKING

from src.grpc.client.retriever_grpc_client import RetrieverGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from protobuf_stubs import retriever_pb2
    from src.domain.models import RetrieveRequest, RetrieveResponse


class RetrieverAdapter:
    def __init__(self) -> None:
        self.client: RetrieverGrpcClient = GrpcClientRegistry().register_client('retriever', RetrieverGrpcClient)


    async def retrieve_context(
        self,
        request: RetrieveRequest
    ) -> RetrieveResponse:
        return await self.client.retrieve_context(request)


    async def health_check(self) -> "retriever_pb2.HealthResponse":
        return await self.client.health_check()


