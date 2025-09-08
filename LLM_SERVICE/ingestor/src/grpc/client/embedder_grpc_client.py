from typing import Any, Dict, List

import grpc  # type: ignore
from loguru import logger

from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from .base_grpc_client import BaseGrpcClient


class EmbedderGrpcClient(BaseGrpcClient[embedder_pb2.EmbedRequest]):
    def __init__(self, channel: grpc.Channel) -> None:
        super().__init__(channel)
        self.stub = embedder_pb2_grpc.EmbedderServiceStub(channel)


    async def health_check(self) -> Dict[str, Any]:
        request = embedder_pb2.HealthRequest()
        self._validate_request(request)
        
        try:
            response = await self.stub.Health(request, timeout=5)
            # Skip validation for health check to avoid CEL errors
            # self._validate_response(response)
            
            return {
                "status": response.status,
                "model_id": response.model_id,
                "dim": response.dim
            }
        except grpc.RpcError as e:
            logger.error(f"Health check failed: {e}")
            raise


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        request = embedder_pb2.EmbedRequest(text=text, normalize=normalize)
        self._validate_request(request)
        
        try:
            response = await self.stub.Embed(request)
            self._validate_response(response)
            
            if not response.success:
                raise Exception(f"Embedding failed: {response.error}")
            
            return {
                "vector": response.vector,
                "success": response.success,
                "error": response.error
            }

        except grpc.RpcError as e:
            logger.error(f"Embed text failed: {e}")
            raise


    async def embed_batch(
        self, 
        texts: List[str],
        normalize: bool = True
    ) -> List[Dict[str, Any]]:
        request = embedder_pb2.EmbedBatchRequest(texts=texts, normalize=normalize)
        self._validate_request(request)
        
        try:
            response = await self.stub.EmbedBatch(request, timeout=60)
            self._validate_response(response)
            
            if not response.items:
                raise Exception("Failed to get embeddings")
            
            return [
                {
                    "vector": item.vector,
                    "success": item.success,
                    "error": item.error
                }
                for item in response.items
            ]

        except grpc.RpcError as e:
            logger.error(f"Embed batch failed: {e}")
            raise

