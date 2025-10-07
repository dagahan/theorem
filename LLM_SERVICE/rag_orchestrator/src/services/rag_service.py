from __future__ import annotations
import time
from typing import Any, Dict, List, TypedDict, TYPE_CHECKING
from loguru import logger

from src.core.logging import MCPLogger

if TYPE_CHECKING:
    from src.adapters.rag_orchestrator_client import RagOrchestratorClient  # type: ignore[import-not-found]


class SourceChunk(TypedDict):
    doc_id: str
    paragraph_id: int
    chunk_id: int
    text: str
    pages: List[int]
    score: float


class DigestItem(TypedDict):
    title: str
    summary: str
    source_chunk: SourceChunk


class RagService:
    def __init__(self, client: "RagOrchestratorClient") -> None:
        self._client = client


    async def search(
        self,
        *,
        query: str,
        collection_name: str,
        top_k: int,
        max_context_chars: int,
        summarizer_prompt: str,
    ) -> List[DigestItem]:
        start_time = time.time()
        
        logger.info(f"RAG search started: query='{query[:100]}...', collection='{collection_name}', top_k={top_k}")
        
        response = await self._client.rag_search(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            max_context_chars=max_context_chars,
            summarizer_prompt=summarizer_prompt,
        )

        if not response.success:
            logger.error(f"RAG search failed: {response.error}")
            raise RuntimeError(f"RAG search failed: {response.error}")

        digests: List[DigestItem] = []

        for digest in response.digests:
            digests.append({
                "title": digest.title,
                "summary": digest.summary,
                "source_chunk": {
                    "doc_id": digest.source_chunk.doc_id,
                    "paragraph_id": digest.source_chunk.paragraph_id,
                    "chunk_id": digest.source_chunk.chunk_id,
                    "text": digest.source_chunk.text,
                    "pages": list(digest.source_chunk.pages),
                    "score": digest.source_chunk.score,
                }
            })

        execution_time_ms = (time.time() - start_time) * 1000
        logger.info(f"RAG search completed: {len(digests)} digests in {execution_time_ms:.2f}ms")
        
        # Логируем детальную информацию о поиске
        MCPLogger.log_rag_search(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            max_context_chars=max_context_chars,
            digests=digests,
            execution_time_ms=execution_time_ms
        )

        return digests


