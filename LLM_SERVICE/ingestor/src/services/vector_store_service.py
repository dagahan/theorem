from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid5, NAMESPACE_URL
from loguru import logger

from src.data_classes.data_classes import Chunk, EmbeddedChunk  # noqa: TC001
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


    def build_point_structs_from_embedded_chunks(
        self,
        embedded_chunks: List[EmbeddedChunk],
        doc_id: str,
        pdf_metadata: Dict[str, Any]
    ) -> List[qm.PointStruct]:
        point_structs: List[qm.PointStruct] = []
        
        for i, embedded_chunk in enumerate(embedded_chunks):
            if not embedded_chunk.success:
                logger.warning(f"Skipping failed embedded chunk {i}")
                continue
                
            if not embedded_chunk.vector:
                logger.warning(f"No vector found for embedded chunk {i}")
                continue
                
            point_id = str(uuid5(NAMESPACE_URL, f"{doc_id}|{i+1}|{i+1}"))
            point_struct = qm.PointStruct(
                id=point_id,
                vector=embedded_chunk.vector,
                payload={
                    "doc_id": doc_id,
                    "paragraph_id": i + 1,
                    "chunk_id": i + 1,
                    "text": embedded_chunk.text,
                    **pdf_metadata,
                    **embedded_chunk.meta
                }
            )

            point_structs.append(point_struct)

        logger.debug(f"Built {len(point_structs)} point structs from embedded chunks")
        return point_structs


    async def upsert_batched_to_collection(
        self,
        collection_name: str,
        point_structs: List[qm.PointStruct]
    ) -> None:
        if not point_structs:
            logger.warning("No point structs to upsert")
            return
            
        logger.debug(f"Upserting {len(point_structs)} point structs to collection {collection_name}")
        b = max(1, self.qdrant_upsert_batch)
        for i in range(0, len(point_structs), b):
            batch = point_structs[i : i + b]
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


