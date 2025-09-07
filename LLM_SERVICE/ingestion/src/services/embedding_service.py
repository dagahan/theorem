import grpc  # type: ignore
from typing import List, Dict, Any

from loguru import logger
from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from src.core.utils import EnvTools


class EmbeddingService:
    def __init__(self) -> None:
        embedder_host: str = EnvTools.get_service_ip("embedder")
        embedder_port: int = int(EnvTools.get_service_port("embedder"))
        
        channel = grpc.aio.insecure_channel(f"{embedder_host}:{embedder_port}")
        self.stub = embedder_pb2_grpc.EmbedderServiceStub(channel)


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:

        request = embedder_pb2.EmbedRequest(text=text, normalize=normalize)
        response = await self.stub.Embed(request)
        
        if not response.success:
            raise Exception(f"Embedding failed: {response.error}")
        
        return {
            "vector": response.vector,
            "success": response.success,
            "error": response.error
        }


    async def embed_batch(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[Dict[str, Any]]:
    
        request = embedder_pb2.EmbedBatchRequest(texts=texts, normalize=normalize)
        response = await self.stub.EmbedBatch(request, timeout=60)
        
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


    async def health_check(self) -> Dict[str, Any]:
        request = embedder_pb2.HealthRequest()
        response = await self.stub.Health(request, timeout=5)
        
        return {
            "status": response.status,
            "model_id": response.model_id,
            "dim": response.dim
        }


