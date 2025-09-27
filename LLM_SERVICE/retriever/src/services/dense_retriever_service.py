from __future__ import annotations

from typing import Any, Dict, List

from src.adapters.embedder_adapter import EmbedderAdapter
from src.adapters.vector_store_adapter import VectorStoreAdapter
from src.domain.models import Candidate, EmbeddingResult, VectorSearchResult


class DenseRetrieverService:
    def __init__(self) -> None:
        self.embedder_adapter = EmbedderAdapter()
        self.vector_store_adapter = VectorStoreAdapter()


    async def retrieve_ann_candidates(
        self,
        query_text: str,
        collection_name: str,
        top_k: int
    ) -> List[Candidate]:
        embedding_result: EmbeddingResult = await self._get_embedding(query_text)
        
        if not embedding_result.success:
            return []

        vector_search_result: VectorSearchResult = await self._search_vectors(
            collection_name,
            embedding_result.vector,
            top_k
        )

        candidates: List[Candidate] = self._convert_to_candidates(vector_search_result.raw_results)

        return candidates


    async def _get_embedding(
        self,
        query_text: str
    ) -> EmbeddingResult:
        try:
            embed_response: Dict[str, Any] = await self.embedder_adapter.embed_text(
                query_text,
                normalize=True
            )

            vector: List[float] = embed_response.get("vector", [])
            
            if not vector:
                return EmbeddingResult(
                    text=query_text,
                    vector=[],
                    success=False,
                    error="Empty vector returned from embedder"
                )
            
            return EmbeddingResult(
                text=query_text,
                vector=vector,
                success=True
            )

        except Exception as e:
            return EmbeddingResult(
                text=query_text,
                vector=[],
                success=False,
                error=str(e)
            )


    async def _search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int
    ) -> VectorSearchResult:

        raw_results: List[Dict[str, Any]] = await self.vector_store_adapter.search(
            collection_name,
            query_vector,
            top_k
        )
        
        return VectorSearchResult(
            query_vector=query_vector,
            raw_results=raw_results,
            total_found=len(raw_results)
        )


    def _convert_to_candidates(
        self,
        raw_results: List[Dict[str, Any]]
    ) -> List[Candidate]:
        candidates: List[Candidate] = []

        for rank_position, item in enumerate(raw_results, start=1):
            payload: Dict[str, Any] = item.get("payload", item)
            doc_id: str = str(payload.get("doc_id", ""))
            
            paragraph_id_raw = payload.get("paragraph_id")
            chunk_id_raw = payload.get("chunk_id")
            
            if paragraph_id_raw is None or chunk_id_raw is None:
                raise ValueError(f"Missing paragraph_id or chunk_id in payload: {payload.keys()}")
                
            paragraph_id: int = int(paragraph_id_raw)
            chunk_id: int = int(chunk_id_raw)
            text: str = payload.get("text", "")
            pages: List[int] = [int(page) for page in payload.get("pages", [])]
            
            score_or_distance: float = float(item.get("score", item.get("distance", 0.0)))
            ann_score: float = -score_or_distance if "distance" in item else score_or_distance

            candidate = Candidate(
                key=(doc_id, paragraph_id, chunk_id),
                text=text,
                pages=pages,
                payload=payload,
                score_ann=ann_score,
                rank_ann=rank_position,
            )

            candidates.append(candidate)

        return candidates
