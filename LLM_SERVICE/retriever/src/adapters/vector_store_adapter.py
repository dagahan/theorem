from __future__ import annotations
from typing import Any, Dict, List
from src.services.vector_store_service import VectorStoreService


class VectorStoreAdapter:
    def __init__(self) -> None:
        self._store = VectorStoreService()


    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        return await self._store.search_documents(
            query_vector=query_vector,
            collection_name=collection_name,
            top_k=top_k,
            score_threshold=0.0,
            quality_filter=True
        )


