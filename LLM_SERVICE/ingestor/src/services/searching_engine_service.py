from __future__ import annotations

from typing import Any, Dict, List, Optional
from loguru import logger

from src.services.health_service import HealthService
from src.services.vector_store_service import VectorStoreService
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


class SearchingEngineService:
    def __init__(self, database_connector: "DataBaseConnector") -> None:
        self.health_service = HealthService(database_connector)
        self.vector_store_service = VectorStoreService()
        self.embedder_grpc_client = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)


    async def search_documents(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit_k: int = 25,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        if await self.health_service.health_check_service("qdrant") != "healthy":
            return []
    
        if collection_name is None:
            collection_name = self.vector_store_service.collection_name

        health_result = await self.health_service.health_check_service("all")

        if isinstance(health_result, tuple) and len(health_result) == 4:
            embedder_health, qdrant_status, postgres_health, s3_status = health_result
            embedder_status = embedder_health.get("status", "unknown")
        else:
            raise RuntimeError("Unexpected health check result format")
        
        if embedder_status != "healthy":
            raise RuntimeError(f"Embedder service unavailable: {embedder_status}")

        if qdrant_status != "healthy":
            raise RuntimeError(f"Vector store service unavailable: {qdrant_status}")

        embedding = await self.embedder_grpc_client.embed_text(
            query,
            normalize=True
        )
        
        logger.debug(f"Embedding created: vector_len={len(embedding.get('vector', []))}, success={embedding.get('success', False)}")

        result = await self.vector_store_service.search_documents(
            query_vector=embedding["vector"],
            collection_name=collection_name,
            limit=limit_k,
            score_threshold=score_threshold
        )

        logger.debug(f"Search result: found {len(result)} results for query '{query}' in collection '{collection_name}'")
        return result


    async def search_with_context(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 25,
        neighbor_window: int = 2,
        include_whole_paragraph: bool = True
    ) -> Dict[str, Any]:
        if await self.health_service.health_check_service("qdrant") != "healthy":
            return {"status": "unsuccessful"}

        if collection_name is None:
            collection_name = self.vector_store_service.collection_name

        hits = await self.search_documents(
            query,
            collection_name,
            limit_k=top_k,
            score_threshold=0.0
        )

        added = set()
        gathered: List[Dict[str, Any]] = []

        for hit in hits:
            p = hit.get("payload", {}) or {}
            doc_id = p.get("doc_id")
            paragraph_id = p.get("paragraph_id")
            chunk_id = p.get("chunk_id")

            if not (doc_id and paragraph_id and chunk_id):
                continue

            if include_whole_paragraph:
                para = await self.vector_store_service.get_paragraph_chunks(collection_name, doc_id, int(paragraph_id))
                for item in para:
                    key = (item["payload"]["doc_id"], item["payload"]["chunk_id"])
                    if key not in added:
                        added.add(key)
                        gathered.append(item)

            start_id = max(1, int(chunk_id) - neighbor_window)
            end_id = int(chunk_id) + neighbor_window
            win = await self.vector_store_service.get_window_by_chunk_id(collection_name, doc_id, start_id, end_id)

            for item in win:
                key = (item["payload"]["doc_id"], item["payload"]["chunk_id"])
                if key not in added:
                    added.add(key)
                    gathered.append(item)

        gathered.sort(key=lambda x: (x["payload"]["doc_id"], x["payload"]["paragraph_id"], x["payload"]["chunk_id"]))

        merged_lines: List[str] = []
        last_para: tuple[str, int] | None = None

        for g in gathered:
            pid = (g["payload"]["doc_id"], g["payload"]["paragraph_id"])
            if last_para is not None and pid != last_para:
                merged_lines.append("")
            merged_lines.append(g["payload"]["text"])
            last_para = pid

        return {
            "chunks": gathered,
            "merged_text": "\n".join(merged_lines)
        }


