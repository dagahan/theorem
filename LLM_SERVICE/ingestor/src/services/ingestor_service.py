from typing import List, Dict, Any, Optional, Union
from loguru import logger
import json
import os
import asyncio

from src.services.chunking_service import ChunkingService
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.services.vector_store_service import VectorStoreService
from src.core.utils import EnvTools, FileSystemTools
from pydantic_schemas.service_stats import ServiceStats
from pydantic_schemas.common import HealthResponse


class IngestorService:
    def __init__(self) -> None:
        self.chunking_service = ChunkingService()
        self.embedder_grpc_client = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)
        self.vector_store_service = VectorStoreService()
        self.collection_name = EnvTools.required_load_env_var("QDRANT_COLLECTION_NAME")
        self.dimensions: int = int(EnvTools.required_load_env_var("EMBEDDER_DIMENSIONS"))


    async def health_check_service(
        self,
        service_name: str 
    ) -> Union[str, tuple[Dict[str, Any], str]]:

        async def _check_embedder_health() -> Dict[str, Any]:
            try:
                embedder_health = await self.embedder_grpc_client.health_check()
                return embedder_health
            except Exception as e:
                logger.warning(f"Embedder health check failed: {e}")
                return {"status": "unhealthy", "model_id": "", "dim": 0}
        
        async def _check_qdrant_health() -> str:
            try:
                vector_store_health = await self.vector_store_service.health_check()
                status: str = vector_store_health.get("status", "unknown")
                return status
            except Exception as e:
                logger.warning(f"Qdrant health check failed: {e}")
                return "unhealthy"
        
        match service_name.lower():
            case "embedder":
                embedder_health = await _check_embedder_health()
                return str(embedder_health.get("status", "unknown"))
                
            case "qdrant":
                return await _check_qdrant_health()
                
            case "all":
                embedder_health, qdrant_status = await asyncio.gather(
                    _check_embedder_health(),
                    _check_qdrant_health(),
                    return_exceptions=False
                )
                return (embedder_health, qdrant_status)
                
            case _:
                raise ValueError(f"Unknown service name: {service_name}")
                    

    async def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any],
        collection_name: Optional[str] = None
    ) -> None:
        if collection_name is None:
            collection_name = self.collection_name

        chunks = self.chunking_service.chunk_document(doc_id, text, metadata)

        health_result = await self.health_check_service("all")
        if isinstance(health_result, tuple) and len(health_result) == 2:
            embedder_health, qdrant_status = health_result
            embedder_status = embedder_health.get("status", "unknown")
        else:
            raise RuntimeError("Unexpected health check result format")
        
        if embedder_status != "healthy" or qdrant_status != "healthy":
            raise RuntimeError(f"Services unavailable. Embedder: {embedder_status}, Qdrant: {qdrant_status}")
        
        self.vector_store_service.ensure_collection(collection_name, vector_size=self.dimensions)
        
        texts = [c["text"] for c in chunks]

        embeds = await self.embedder_grpc_client.embed_batch(texts, normalize=True)
        if len(embeds) != len(chunks):
            raise RuntimeError("Embedding count mismatch")

        points = []
        for c, e in zip(chunks, embeds):
            points.append({
                "vector": e["vector"],
                "payload": {
                    "doc_id": c["doc_id"],
                    "paragraph_id": c["paragraph_id"],
                    "chunk_id": c["chunk_id"],
                    "text": c["text"],
                    "metadata": c["metadata"],
                }
            })

        await self.vector_store_service.upsert_points(collection_name, points)


    async def search_documents(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit: int = 25,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        if await self.health_check_service("qdrant") != "healthy":
            return []
    
        if collection_name is None:
            collection_name = self.collection_name

        health_result = await self.health_check_service("all")
        if isinstance(health_result, tuple) and len(health_result) == 2:
            embedder_health, qdrant_status = health_result
            embedder_status = embedder_health.get("status", "unknown")
        else:
            raise RuntimeError("Unexpected health check result format")
        
        if embedder_status != "healthy":
            raise RuntimeError(f"Embedder service unavailable: {embedder_status}")
        if qdrant_status != "healthy":
            raise RuntimeError(f"Vector store service unavailable: {qdrant_status}")

        embedding = await self.embedder_grpc_client.embed_text(query, normalize=True)

        result = await self.vector_store_service.search(
            collection_name=collection_name,
            query_vector=embedding["vector"],
            limit=limit,
            score_threshold=score_threshold
        )
        return result


    async def search_with_context(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 25,
        neighbor_window: int = 2,
        include_whole_paragraph: bool = True
    ) -> Dict[str, Any]:
        if await self.health_check_service("qdrant") != "healthy":
            return {"status": "unsuccessful"}

        if collection_name is None:
            collection_name = self.collection_name

        hits = await self.search_documents(query, collection_name, limit=top_k, score_threshold=0.0)

        added = set()
        gathered: List[Dict[str, Any]] = []

        for h in hits:
            p = h.get("payload", {}) or {}
            doc_id = p.get("doc_id")
            paragraph_id = p.get("paragraph_id")
            chunk_id = p.get("chunk_id")

            if not (doc_id and paragraph_id and chunk_id):
                continue

            if include_whole_paragraph:
                para = await self.vector_store_service.get_paragraph_chunks(collection_name, doc_id, paragraph_id)
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


    async def delete_document(
        self,
        doc_id: str,
        collection_name: Optional[str] = None
    ) -> Dict[str, str]:
        if await self.health_check_service("qdrant") != "healthy":
            return {"status": "unsuccessful", "doc_id": doc_id}

        if collection_name is None:
            collection_name = self.collection_name
            
        await self.vector_store_service.delete_document(collection_name, doc_id)
        return {"status": "deleted", "doc_id": doc_id}


    async def list_collections(self) -> List[str]:
        if await self.health_check_service("qdrant") != "healthy":
            return []

        collections = await self.vector_store_service.get_collections()
        return [c["name"] for c in collections]


    async def get_document_chunks_count(
        self,
        doc_id: str,
        collection_name: Optional[str] = None
    ) -> int:
        if await self.health_check_service("qdrant") != "healthy":
            return 0

        if collection_name is None:
            collection_name = self.collection_name
        result = await self.vector_store_service.get_document_chunks_count(collection_name, doc_id)
        return result


    async def get_service_stats(self) -> ServiceStats:
        total_collections = 0
        total_vectors = 0
        error_messages = []
        
        try:
            health_result = await self.health_check_service("all")
            if isinstance(health_result, tuple) and len(health_result) == 2:
                embedder_health, qdrant_status = health_result
                embedder_status = embedder_health.get("status", "unknown")
                embedder_model_id = embedder_health.get("model_id", "")
                embedder_dim = embedder_health.get("dim", 0)
            else:
                raise ValueError("Unexpected health check result format")
                    
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            embedder_status = "unknown"
            embedder_model_id = ""
            embedder_dim = 0
            qdrant_status = "unknown"
            error_messages.append(f"Health check failed: {str(ex)}")
        
        if qdrant_status == "healthy":
            try:
                collections = await self.vector_store_service.get_collections()
                total_collections = len(collections)
                total_vectors = sum(col.get("vectors_count", 0) for col in collections)
                logger.debug(f"Retrieved {total_collections} collections with {total_vectors} total vectors")
                
            except Exception as e:
                error_messages.append(f"Failed to get collections: {str(e)}")
                logger.warning(f"Failed to get collections: {e}")
        else:
            error_messages.append("Skipping collection stats due to unhealthy vector store")
        
        return ServiceStats(
            total_collections=total_collections,
            total_vectors=total_vectors,
            embedder_status=embedder_status,
            embedder_model_id=embedder_model_id,
            embedder_dim=embedder_dim,
            qdrant_status=qdrant_status,
            error_message="; ".join(error_messages) if error_messages else ""
        )


