from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from src.adapters.hybrid_embedder_adapter import HybridEmbedderAdapter
from src.adapters.vector_store_adapter import VectorStoreAdapter
from src.pydantic_schemas.retriever import Candidate


class SparseRetrieverService:
    def __init__(self) -> None:
        self.hybrid_embedder_adapter = HybridEmbedderAdapter()
        self.vector_store_adapter = VectorStoreAdapter()


    async def retrieve_sparse_candidates(
        self,
        query_text: str,
        collection_name: str,
        top_k: int
    ) -> List[Candidate]:
        sparse_embedding = await self._get_sparse_embedding(query_text)
        
        if not sparse_embedding["success"]:
            return []

        sparse_search_result = await self._search_sparse_vectors(
            collection_name,
            sparse_embedding["indices"],
            sparse_embedding["values"],
            top_k
        )

        candidates: List[Candidate] = self._convert_to_candidates(sparse_search_result)

        return candidates


    async def _get_sparse_embedding(
        self,
        query_text: str
    ) -> Dict[str, Any]:
        try:
            sparse_response: Dict[str, Any] = await self.hybrid_embedder_adapter.embed_text_sparse(query_text)

            if not sparse_response.get("success", False):
                return {
                    "success": False,
                    "error": sparse_response.get("error", "Sparse embedding failed")
                }
            
            return {
                "success": True,
                "indices": sparse_response.get("indices", []),
                "values": sparse_response.get("values", [])
            }

        except Exception as e:
            logger.error(f"Sparse retrieval embedding failed for query '{query_text}': {e}")
            return {
                "success": False,
                "error": str(e)
            }


    async def _search_sparse_vectors(
        self,
        collection_name: str,
        indices: List[int],
        values: List[float],
        top_k: int
    ) -> List[Dict[str, Any]]:
        return await self.vector_store_adapter.search_sparse(
            collection_name,
            indices,
            values,
            top_k
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
            
            score: float = float(item.get("score", 0.0))

            candidate = Candidate(
                key=(doc_id, paragraph_id, chunk_id),
                text=text,
                pages=pages,
                payload=payload,
                score_bm25=score,
                rank_bm25=rank_position,
            )

            candidates.append(candidate)

        return candidates
