from __future__ import annotations
from typing import List, Dict, Any
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry


class EmbedderAdapter:
    def __init__(self) -> None:
        self.embedder_client: EmbedderGrpcClient = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        return await self.embedder_client.embed_text(
            text,
            normalize=normalize
        )


