from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
import json
from datetime import datetime

from src.services.chunking_service import ChunkingService
from src.services.embedding_service import EmbeddingService
from src.services.vector_store_service import VectorStoreService
from src.grpc.client.registry_grpc_clients import RegistryGrpcClients
from src.core.utils import EnvTools
from pydantic_schemas.service_stats import ServiceStats
from pydantic_schemas.common import HealthResponse


class IngestorService:
    def __init__(self, grpc_clients: RegistryGrpcClients) -> None:
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService(grpc_clients)
        self.vector_store_service = VectorStoreService()
        self.collection_name = EnvTools.required_load_env_var("QDRANT_COLLECTION_NAME")


    def _log_processing_results(
        self,
        doc_id: str,
        filename: str,
        extracted_text: str,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> None:
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "filename": filename,
                "metadata": metadata,
                "extracted_text_length": len(extracted_text),
                "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
                "chunks_count": len(chunks),
                "chunks": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "paragraph_id": chunk["paragraph_id"],
                        "text_length": len(chunk["text"]),
                        "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
                    }
                    for chunk in chunks
                ]
            }
            
            with open("test.txt", "a", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write(f"PROCESSING LOG - {log_entry['timestamp']}\n")
                f.write("=" * 80 + "\n")
                f.write(json.dumps(log_entry, indent=2, ensure_ascii=False))
                f.write("\n\n")
                
            logger.info(f"Processing results logged to test.txt for doc_id: {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to log processing results: {e}")


    async def health_check(self) -> HealthResponse:
        try:
            result = await self.vector_store_service.health_check()
            return HealthResponse(status=result["status"])
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthResponse(status="unhealthy", error=str(e))


    async def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any],
        collection_name: Optional[str] = None
    ) -> None:
        if collection_name is None:
            collection_name = self.collection_name

        # Log processing results BEFORE any embedding calls
        chunks = self.chunking_service.chunk_document(doc_id, text, metadata)
        filename = metadata.get("filename", "unknown")
        self._log_processing_results(doc_id, filename, text, chunks, metadata)

        # Now try to connect to embedder service
        health = await self.embedding_service.health_check()
        dim = int(health["dim"])
        
        self.vector_store_service.ensure_collection(collection_name, vector_size=dim)
        
        texts = [c["text"] for c in chunks]

        embeds = await self.embedding_service.embed_batch(texts, normalize=True)
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


    async def _process_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> None:
        await self.ingest_document(doc_id, text, metadata, self.collection_name)


    async def search_documents(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit: int = 25,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        if collection_name is None:
            collection_name = self.collection_name

        emb = await self.embedding_service.embed_text(query, normalize=True)

        return await self.vector_store_service.search(
            collection_name=collection_name,
            query_vector=emb["vector"],
            limit=limit,
            score_threshold=score_threshold
        )


    async def search_with_context(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 25,
        neighbor_window: int = 2,
        include_whole_paragraph: bool = True
    ) -> Dict[str, Any]:
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
        last_para: Tuple[str, int] | None = None

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
        if collection_name is None:
            collection_name = self.collection_name
            
        await self.vector_store_service.delete_document(collection_name, doc_id)
        return {"status": "deleted", "doc_id": doc_id}


    async def list_collections(self) -> List[str]:
        cols = await self.vector_store_service.get_collections()
        return [c["name"] for c in cols]


    async def get_document_chunks_count(self, doc_id: str, collection_name: Optional[str] = None) -> int:
        if collection_name is None:
            collection_name = self.collection_name
        return await self.vector_store_service.get_document_chunks_count(collection_name, doc_id)


    async def get_service_stats(self) -> ServiceStats:
        collections = await self.vector_store_service.get_collections()
        total_collections = len(collections)
        total_vectors = sum(col["vectors_count"] for col in collections)
        
        embedder_health = await self.embedding_service.health_check()
        vector_store_health = await self.vector_store_service.health_check()
        
        return ServiceStats(
            total_collections=total_collections,
            total_vectors=total_vectors,
            embedder_status=embedder_health["status"],
            qdrant_status=vector_store_health["status"]
        )


