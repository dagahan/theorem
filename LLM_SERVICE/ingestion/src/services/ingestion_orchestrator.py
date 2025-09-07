from typing import List, Dict, Any, Tuple
from loguru import logger

from src.services.chunking_service import ChunkingService
from src.services.embedding_service import EmbeddingService
from src.services.vector_store_service import VectorStoreService
from src.core.utils import EnvTools


class IngestionOrchestrator:
    def __init__(self) -> None:
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.vector_store_service = VectorStoreService()
        self.default_collection = EnvTools.required_load_env_var("QDRANT_COLLECTION_NAME")


    async def ingest_document(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any],
        collection_name: str
    ) -> None:

        health = await self.embedding_service.health_check()
        dim = int(health["dim"])
        
        self.vector_store_service.ensure_collection(collection_name, vector_size=dim)

        chunks = self.chunking_service.chunk_document(doc_id, text, metadata)
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


    async def search_documents(
        self,
        query: str,
        collection_name: str,
        limit: int = 25,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:

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
        collection_name: str,
        top_k: int = 25,
        neighbor_window: int = 2,
        include_whole_paragraph: bool = True
    ) -> Dict[str, Any]:

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
        collection_name: str
    ) -> None:
        await self.vector_store_service.delete_document(collection_name, doc_id)


    async def get_service_stats(self) -> Dict[str, Any]:
        collections = await self.vector_store_service.get_collections()
        total_collections = len(collections)
        total_vectors = sum(col["vectors_count"] for col in collections)
        
        embedder_health = await self.embedding_service.health_check()
        vector_store_health = await self.vector_store_service.health_check()
        
        return {
            "total_collections": total_collections,
            "total_vectors": total_vectors,
            "embedder_status": embedder_health["status"],
            "qdrant_status": vector_store_health["status"]
        }


