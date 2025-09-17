from __future__ import annotations
from typing import List, Dict, Any
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

class EmbedderAdapter:
    def __init__(self) -> None:
        self._client: EmbedderGrpcClient = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        return await self._client.embed_text(text, normalize=normalize)


    async def embed_texts(
        self,
        texts: List[str],
        normalize: bool = True
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for t in texts:
            out.append(await self._client.embed_text(t, normalize=normalize))
        return out


