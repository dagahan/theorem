from typing import Any, Dict, Any

import grpc  # type: ignore
import grpc.aio  # type: ignore
from loguru import logger

from protobuf_stubs import hybrid_embedder_pb2, hybrid_embedder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools


class HybridEmbedderGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str, **kwargs: Any) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.stub = hybrid_embedder_pb2_grpc.HybridEmbedderServiceStub(self.channel)


    async def health_check(self) -> Dict[str, Any]:
        request = hybrid_embedder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.Health(request, timeout=3)
            GrpcTools.validate_proto(response)
            return GrpcTools.proto_to_dict(response)
        except grpc.aio.AioRpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            raise


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        request = hybrid_embedder_pb2.DenseEmbedRequest(text=text)
        GrpcTools.validate_proto(request)
        
        try:
            response = await self.stub.DenseEmbed(request)
            if not response.success:
                raise RuntimeError(f"Dense embedding failed: {response.error}")

            GrpcTools.validate_proto(response)
            return GrpcTools.proto_to_dict(response)
        except grpc.aio.AioRpcError as ex:
            logger.error(f"Dense embed text failed: {ex}")
            raise


    async def embed_text_sparse(
        self,
        text: str
    ) -> Dict[str, Any]:
        request = hybrid_embedder_pb2.SparseEmbedRequest(text=text)
        GrpcTools.validate_proto(request)
        
        try:
            response = await self.stub.SparseEmbed(request)
            if not response.success:
                raise RuntimeError(f"Sparse embedding failed: {response.error}")

            GrpcTools.validate_proto(response)
            return GrpcTools.proto_to_dict(response)
        except grpc.aio.AioRpcError as ex:
            logger.error(f"Sparse embed text failed: {ex}")
            raise
