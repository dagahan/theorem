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
        logger.debug(f"Building points: {len(chunks)} chunks, {len(embeds)} embeds")
        
        for i, (ch, em) in enumerate(zip(chunks, embeds)):
            if not em.get("success", False):
                logger.warning(f"Skipping failed embed for chunk {i}")
                continue
                
            vector = em.get("vector", [])
            if not vector:
                logger.warning(f"No vector found for chunk {i}")
                continue
                
            pid = str(uuid5(NAMESPACE_URL, f"{ch['doc_id']}|{ch['paragraph_id']}|{ch['chunk_id']}"))
            points.append(qm.PointStruct(
                id=pid,
                vector=vector,
                payload={
                    "doc_id": ch["doc_id"],
                    "paragraph_id": ch["paragraph_id"],
                    "chunk_id": ch["chunk_id"],
                    "text": ch["text"],
                    "pages": ch.get("pages", []),
                    "page_anchor": ch.get("page_anchor"),
                    "parent_type": ch.get("parent_type"),
                },
            ))

        logger.debug(f"Built {len(points)} points")
        return points


    async def upsert_batched_to_collection(
        self,
        collection_name: str,
        points: List[qm.PointStruct]
    ) -> None:
        if not points:
            logger.warning("No points to upsert")
            return
            
        logger.debug(f"Upserting {len(points)} points to collection {collection_name}")
        b = max(1, self.qdrant_upsert_batch)
        for i in range(0, len(points), b):
            batch = points[i : i + b]
            logger.debug(f"Upserting batch {i//b + 1}: {len(batch)} points")
            await self.qdrant_grpc_client.upsert_points(collection_name, batch)


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




    async def get_collection_documents(
        self,
        collection_name: str
    ) -> List[str]:
        return await self.qdrant_grpc_client.get_collection_documents(collection_name)




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


