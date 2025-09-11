from __future__ import annotations
import os
import re
import unicodedata
from typing import List, Dict, Any, Optional, Union, Tuple
from loguru import logger
import asyncio
from uuid import uuid5, NAMESPACE_URL

from src.services.chunking_service import ChunkingService
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.qdrant_grpc_client import QdrantGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.core.utils import EnvTools
from pydantic_schemas.service_stats import ServiceStats
from qdrant_client.http import models as qm


class IngestorService:
    def __init__(self) -> None:
        self.chunking_service = ChunkingService()
        self.embedder_grpc_client = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)
        self.qdrant_grpc_client = GrpcClientRegistry().register_client("qdrant", QdrantGrpcClient)
        self.collection_name = EnvTools.required_load_env_var("QDRANT_COLLECTION_NAME")
        self.dimensions: int = int(EnvTools.required_load_env_var("EMBEDDER_DIMENSIONS"))
        self.qdrant_upsert_batch: int = int(EnvTools.required_load_env_var("QDRANT_UPSERT_BATCH"))


    @staticmethod
    def _slug_from_filename(meta: Dict[str, Any]) -> str:
        name = str(meta.get("filename", "")).strip()
        stem = os.path.splitext(os.path.basename(name))[0]
        if not stem:
            raise ValueError("Cannot determine doc_id from filename.")
        norm = unicodedata.normalize("NFKC", stem).lower()
        norm = re.sub(r"\s+", "_", norm)
        norm = re.sub(r"[^a-z0-9\u0400-\u04FF_\-\.]", "-", norm).strip("-. _")
        if not norm:
            raise ValueError("Empty doc_id after filename normalization.")
        return norm


    async def health_check_service(
        self, service_name: str
    ) -> Union[str, Tuple[Dict[str, Any], str]]:
        async def _check_embedder() -> Dict[str, Any]:
            try:
                return await self.embedder_grpc_client.health_check()
            except Exception as ex:
                logger.warning(f"Embedder health check failed: {ex}")
                return {"status": "unhealthy", "model_id": "", "dim": 0}

        async def _check_qdrant() -> str:
            try:
                h = await self.qdrant_grpc_client.health_check()
                return str(h.get("status", "unknown"))
            except Exception as e:
                logger.warning(f"Qdrant health check failed: {e}")
                return "unhealthy"

        name = service_name.lower()
        if name == "embedder":
            return str((await _check_embedder()).get("status", "unknown"))
        if name == "qdrant":
            return await _check_qdrant()
        if name == "all":
            emb, q = await asyncio.gather(_check_embedder(), _check_qdrant())
            return emb, q
        raise ValueError(f"Unknown service name: {service_name}")


    async def _ensure_all_healthy(self) -> Dict[str, Any]:
        health = await self.health_check_service("all")
        assert isinstance(health, tuple)
        embedder_health, qdrant_status = health

        if embedder_health.get("status") != "healthy" or qdrant_status != "healthy":
            raise RuntimeError(
                f"Services unavailable. Embedder: {embedder_health.get('status')}, "
                f"Qdrant: {qdrant_status}"
            )
        return embedder_health


    async def _ensure_qdrant_collection(
        self,
        collection_name: str
    ) -> None:
        cols = await self.qdrant_grpc_client.get_collections()
        exists = any(
            (getattr(c, "name", None) or c.get("name")) == collection_name for c in cols
        )
        if not exists:
            await self.qdrant_grpc_client.create_collection(collection_name, self.dimensions)


    def _filter_chunks(
        self,
        raw_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return [
            c
            for c in raw_chunks
            if (t := str(c.get("text", "")).strip()) and 30 <= len(t) <= 8192
        ]


    async def _embed_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        texts = [str(c["text"]) for c in chunks]
        return await self.embedder_grpc_client.embed_batch(texts, normalize=True)


    @staticmethod
    def _build_points(
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
                },
            ))
        return points


    async def _upsert_batched(
        self,
        collection_name: str,
        points: List[qm.PointStruct]
    ) -> None:
        b = max(1, self.qdrant_upsert_batch)
        for i in range(0, len(points), b):
            await self.qdrant_grpc_client.upsert_points(collection_name, points[i : i + b])


    async def ingest_file(
        self,
        file_text: str,
        file_metadata: Dict[str, Any],
        collection_name: Optional[str] = None,
    ) -> None:
        col = collection_name or self.collection_name
        doc_id = self._slug_from_filename(file_metadata)

        await self._ensure_qdrant_collection(col)
        if await self.qdrant_grpc_client.is_document_exists(col, doc_id):
            raise ValueError(f"Document with id '{doc_id}' already exists in collection '{col}'. "
                             f"File name (without extension) must be unique.")

        await self._ensure_all_healthy()

        chunks_raw = self.chunking_service.chunk_file(
            doc_id,
            file_text,
            file_metadata
        )
        if not chunks_raw:
            logger.warning(f"No chunks produced for {doc_id}")
            return

        embeds = await self._embed_chunks(chunks_raw)
        if len(embeds) != len(chunks_raw):
            raise RuntimeError("Embedding count mismatch")

        points = self._build_points(chunks_raw, embeds)
        await self._upsert_batched(col, points)


    async def get_document_embedded(
        self,
        doc_id: str,
        collection_name: Optional[str] = None
    ) -> List[List[float]]:
        col = collection_name or self.collection_name
        return await self.qdrant_grpc_client.get_document_vectors(col, doc_id)


    async def get_document_text(
        self,
        doc_id: str,
        collection_name: Optional[str] = None
    ) -> List[str]:
        col = collection_name or self.collection_name
        return await self.qdrant_grpc_client.get_document_texts(col, doc_id)


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
        logger.debug(f"Embedding created: vector_len={len(embedding.get('vector', []))}, success={embedding.get('success', False)}")

        result = await self.qdrant_grpc_client.search(
            collection_name=collection_name,
            query_vector=embedding["vector"],
            limit=limit,
            score_threshold=score_threshold
        )
        logger.debug(f"Search result: found {len(result)} results for query '{query}' in collection '{collection_name}'")
        return result


    async def get_collection_documents(
        self,
        collection_name: str
    ) -> List[str]:
        if await self.health_check_service("qdrant") != "healthy":
            return []
        
        return await self.qdrant_grpc_client.get_collection_documents(collection_name)


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
                para = await self.qdrant_grpc_client.get_paragraph_chunks(collection_name, doc_id, paragraph_id)
                for item in para:
                    key = (item["payload"]["doc_id"], item["payload"]["chunk_id"])
                    if key not in added:
                        added.add(key)
                        gathered.append(item)

            start_id = max(1, int(chunk_id) - neighbor_window)
            end_id = int(chunk_id) + neighbor_window
            win = await self.qdrant_grpc_client.get_window_by_chunk_id(collection_name, doc_id, start_id, end_id)

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
            
        await self.qdrant_grpc_client.delete_document(collection_name, doc_id)
        return {"status": "deleted", "doc_id": doc_id}


    async def list_collections(self) -> List[Dict[str, Any]]:
        if await self.health_check_service("qdrant") != "healthy":
            return []

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
        collection_name: Optional[str] = None
    ) -> int:
        if await self.health_check_service("qdrant") != "healthy":
            return 0

        if collection_name is None:
            collection_name = self.collection_name
        result = await self.qdrant_grpc_client.get_document_chunks_count(collection_name, doc_id)
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
                collections = await self.qdrant_grpc_client.get_collections()
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


