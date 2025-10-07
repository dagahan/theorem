from __future__ import annotations

from typing import Any, Dict, List

from src.services.vector_store_service import VectorStoreService


class VectorStoreAdapter:
    def __init__(self) -> None:
        self.vector_store_service = VectorStoreService()




    async def search_dense(
        self,
        collection_name: str,
        vector: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        return await self.vector_store_service.search_dense(
            collection_name=collection_name,
            vector=vector,
            limit=top_k
        )


    async def search_sparse(
        self,
        collection_name: str,
        indices: List[int],
        values: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        return await self.vector_store_service.search_sparse(
            collection_name=collection_name,
            indices=indices,
            values=values,
            limit=top_k
        )


