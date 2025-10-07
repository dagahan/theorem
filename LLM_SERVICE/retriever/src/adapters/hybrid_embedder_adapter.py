from __future__ import annotations
from typing import Dict, Any
from src.grpc.client.hybrid_embedder_grpc_client import HybridEmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry


class HybridEmbedderAdapter:
    def __init__(self) -> None:
        self.hybrid_embedder_client: HybridEmbedderGrpcClient = GrpcClientRegistry().register_client(
            "hybrid_embedder",
            HybridEmbedderGrpcClient,
        )


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        return await self.hybrid_embedder_client.embed_text(
            text,
            normalize=normalize
        )


    async def embed_text_sparse(
        self,
        text: str
    ) -> Dict[str, Any]:
        return await self.hybrid_embedder_client.embed_text_sparse(text)
