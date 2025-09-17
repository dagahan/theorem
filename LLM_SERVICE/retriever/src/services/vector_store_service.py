from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid5, NAMESPACE_URL
from loguru import logger

from src.grpc.client.qdrant_grpc_client import QdrantGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.core.utils import EnvTools
from qdrant_client.http import models as qm


class VectorStoreService:
    def __init__(self) -> None:
        self.qdrant_grpc_client = GrpcClientRegistry().register_client("qdrant", QdrantGrpcClient)
        self.dimensions: int = int(EnvTools.required_load_env_var("EMBEDDER_DIMENSIONS"))
        self.qdrant_upsert_batch: int = int(EnvTools.required_load_env_var("QDRANT_UPSERT_BATCH"))


    async def ensure_collection_exists(
        self,
        collection_name: str
    ) -> None:
        cols = await self.qdrant_grpc_client.get_collections()
        exists = any(
            (getattr(c, "name", None) or c.get("name")) == collection_name for c in cols
        )
        if not exists:
            await self.qdrant_grpc_client.create_collection(collection_name, self.dimensions)


    def build_points(
        self,
        chunks: List[Dict[str, Any]],
        embeds: List[Dict[str, Any]]
    ) -> List[qm.PointStruct]:
        points: List[qm.PointStruct] = []
        for ch, em in zip(chunks, embeds):
            pid = str(uuid5(NAMESPACE_URL, f"{ch['doc_id']}|{ch['paragraph_id']}|{ch['chunk_id']}"))
            points.append(qm.PointStruct(
                id=pid,
                vector=em["vector"],
                payload={
                    "doc_id": ch["doc_id"],
                    "paragraph_id": ch["paragraph_id"],
                    "chunk_id": ch["chunk_id"],
                    "text": ch["text"],
                    "meta": ch.get("meta", {}),
                },
            ))

        return points


    async def upsert_batched_to_collection(
        self,
        collection_name: str,
        points: List[qm.PointStruct]
    ) -> None:
        b = max(1, self.qdrant_upsert_batch)
        for i in range(0, len(points), b):
            await self.qdrant_grpc_client.upsert_points(collection_name, points[i : i + b])


    async def is_document_exists(
        self,
        collection_name: str,
        doc_id: str
    ) -> bool:
        return await self.qdrant_grpc_client.is_document_exists(collection_name, doc_id)


    async def get_document_vectors(
        self,
        doc_id: str,
        collection_name: str
    ) -> List[List[float]]:
        return await self.qdrant_grpc_client.get_document_vectors(collection_name, doc_id)


    async def get_document_texts(
        self,
        doc_id: str,
        collection_name: str
    ) -> List[str]:
        return await self.qdrant_grpc_client.get_document_texts(collection_name, doc_id)


    async def search_documents(
        self,
        query_vector: List[float],
        collection_name: str,
        top_k: int = 25,
        score_threshold: float = 0.0,
        quality_filter: bool = True
    ) -> List[Dict[str, Any]]:
        result = await self.qdrant_grpc_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k * 2 if quality_filter else top_k,  # Get more results for filtering
            score_threshold=score_threshold
        )

        if quality_filter:
            result = self._filter_by_quality(result)

        result = result[:top_k]  # Limit to requested top_k
        logger.debug(f"Search result: found {len(result)} results in collection '{collection_name}'")
        return result

    def _filter_by_quality(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for result in results:
            payload = result.get("payload", result)
            
            # Skip low-quality chunks
            if self._is_low_quality_chunk(payload):
                continue
                
            # Boost high-quality chunks
            quality_score = payload.get("meta", {}).get("quality_score", 0.5)
            if quality_score < 0.3:
                continue
                
            # Boost specific parent types for EGE
            parent_type = payload.get("meta", {}).get("parent_type", "")
            if parent_type in {"task", "answer", "heading", "formula"}:
                result["score"] = result.get("score", 0) * 1.2
                
            filtered.append(result)
            
        return filtered

    def _is_low_quality_chunk(self, payload: Dict[str, Any]) -> bool:
        text = payload.get("text", "")
        meta = payload.get("meta", {})
        
        # Check explicit quality flags
        if meta.get("has_cid", False) or meta.get("has_ellipsis", False) or meta.get("has_ocr_spacing", False):
            return True
            
        # Check alpha ratio
        alpha_ratio = meta.get("alpha_ratio", 0.5)
        if alpha_ratio < 0.4:
            return True
            
        # Check text length
        if len(text) < 180:
            return True
            
        return False


    async def get_collection_documents(
        self,
        collection_name: str
    ) -> List[str]:
        return await self.qdrant_grpc_client.get_collection_documents(collection_name)


    async def get_paragraph_chunks(
        self,
        collection_name: str,
        doc_id: str,
        paragraph_id: int
    ) -> List[Dict[str, Any]]:
        return await self.qdrant_grpc_client.get_paragraph_chunks(collection_name, doc_id, paragraph_id)


    async def get_window_by_chunk_id(
        self,
        collection_name: str,
        doc_id: str,
        start_id: int,
        end_id: int
    ) -> List[Dict[str, Any]]:
        return await self.qdrant_grpc_client.get_window_by_chunk_id(collection_name, doc_id, start_id, end_id)


    async def delete_document(
        self,
        doc_id: str,
        collection_name: str
    ) -> None:
        await self.qdrant_grpc_client.delete_document(collection_name, doc_id)
        logger.info(f"Document {doc_id} deleted from Qdrant collection {collection_name}")


    async def get_collections(self) -> List[Dict[str, Any]]:
        collections = await self.qdrant_grpc_client.get_collections()
        result = []
        for c in collections:
            collection_name = None
            if hasattr(c, "name"):
                collection_name = c.name
            elif isinstance(c, dict) and "name" in c:
                collection_name = c["name"]
            
            if collection_name:
                documents = await self.get_collection_documents(collection_name)
                result.append({
                    "name": collection_name,
                    "status": "active",
                    "documents": documents
                })

        return result


    async def get_document_chunks_count(
        self,
        doc_id: str,
        collection_name: str
    ) -> int:
        result = await self.qdrant_grpc_client.get_document_chunks_count(collection_name, doc_id)
        return result


    async def get_collections_stats(self) -> tuple[int, int]:
        collections = await self.qdrant_grpc_client.get_collections()
        total_collections = len(collections)
        total_vectors = sum(col.get("vectors_count", 0) for col in collections)
        logger.debug(f"Retrieved {total_collections} collections with {total_vectors} total vectors")
        return total_collections, total_vectors


