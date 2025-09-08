from typing import List, Dict, Any

from loguru import logger
from src.grpc.client.registry_grpc_clients import RegistryGrpcClients


class EmbeddingService:
    def __init__(self, grpc_clients: RegistryGrpcClients) -> None:
        self.grpc_clients = grpc_clients


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:

        embedder_grpc_client = await self.grpc_clients.get_embedder_client()
        return await embedder_grpc_client.embed_text(text, normalize)


    async def embed_batch(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[Dict[str, Any]]:

        embedder_grpc_client = await self.grpc_clients.get_embedder_client()
        return await embedder_grpc_client.embed_batch(texts, normalize)


    async def health_check(self) -> Dict[str, Any]: 
        client = await self.grpc_clients.get_embedder_client()
        embedder_grpc_client = await self.grpc_clients.get_embedder_client()
        return await embedder_grpc_client.health_check()


