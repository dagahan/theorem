from __future__ import annotations

from typing import Any, List
from loguru import logger

from src.grpc.client.retriever_grpc_client import RetrieverGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry


class RetrieverAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: RetrieverGrpcClient = registry.register_client(
            "retriever",
            RetrieverGrpcClient,
        )

    async def retrieve(
        self,
        question: str,
        collection_name: str,
        top_k: int = 10
    ) -> List[Any]:
        logger.info(f"Retriever search: question='{question[:80]}...', collection='{collection_name}', top_k={top_k}")
        
        response = await self.client.retrieve(
            question=question,
            collection_name=collection_name,
            top_k=top_k
        )

        if not response.success or not response.results:
            logger.warning(f"Retriever failed: {response.error}")
            return []

        logger.info(f"Retriever returned {len(response.results)} results")
        return response.results  # type: ignore[no-any-return]