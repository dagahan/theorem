from __future__ import annotations

from typing import Any, Dict, List
from loguru import logger

from src.grpc.client.qdrant_grpc_client import QdrantGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.core.utils import EnvTools


class VectorStoreService:
    def __init__(self) -> None:
        self.qdrant_grpc_client = GrpcClientRegistry().register_client("qdrant", QdrantGrpcClient)
        self.dimensions: int = int(EnvTools.required_load_env_var("HYBRID_EMBEDDER_DIMENSIONS"))


    async def ensure_collection_exists(
        self,
        collection_name: str
    ) -> None:
        await self.qdrant_grpc_client.ensure_collection_hybrid(collection_name, self.dimensions)


    async def search_dense(
        self,
        collection_name: str,
        vector: List[float],
        limit: int
    ) -> List[Dict[str, Any]]:
        return await self.qdrant_grpc_client.search_dense(collection_name, vector, limit)


    async def search_sparse(
        self,
        collection_name: str,
        indices: List[int],
        values: List[float],
        limit: int
    ) -> List[Dict[str, Any]]:
        return await self.qdrant_grpc_client.search_sparse(collection_name, indices, values, limit)











