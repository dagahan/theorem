from __future__ import annotations

from typing import Any, Dict, Final, List, Tuple

from src.services.vector_store_service import VectorStoreService
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient


class DenseRetrieverService:
    _DEFAULT_SCORE: Final[float] = 0.0

    def __init__(self) -> None:
        self.vector_store: VectorStoreService = VectorStoreService()
        self.embedding_client: EmbedderGrpcClient = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)


    async def retrieve_documents_by_semantic_similarity(
        self,
        query_texts: List[str],
        collection_name: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        document_results: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
        
        for query_text in query_texts:
            embedding_response: Dict[str, Any] = await self.embedding_client.embed_text(query_text, normalize=True)
            query_vector: List[float] = embedding_response.get("vector", [])

            search_results: List[Dict[str, Any]] = await self.vector_store.search_documents(
                query_vector=query_vector,
                collection_name=collection_name,
                top_k=top_k,
                score_threshold=0.0
            )

            for rank_position, search_result in enumerate(search_results, start=1):
                document_payload: Dict[str, Any] = search_result.get("payload", search_result)
                document_id: str | None = document_payload.get("doc_id")
                paragraph_id: int | None = document_payload.get("paragraph_id")
                chunk_id: int | None = document_payload.get("chunk_id")
                document_text: str = document_payload.get("text", "")

                if document_id is None or paragraph_id is None or chunk_id is None:
                    continue

                document_key: Tuple[str, int, int] = (str(document_id), int(paragraph_id), int(chunk_id))
                raw_similarity_score: float = float(search_result.get("score", search_result.get("distance", self._DEFAULT_SCORE)))
                similarity_score: float = -raw_similarity_score if "distance" in search_result else raw_similarity_score
                existing_result: Dict[str, Any] | None = document_results.get(document_key)

                if existing_result is None:
                    document_results[document_key] = {
                        "document_key": document_key,
                        "retrieval_method": "semantic_similarity",
                        "similarity_score": similarity_score,
                        "rank_position": rank_position,
                        "document_data": {
                            "doc_id": document_id, 
                            "paragraph_id": paragraph_id, 
                            "chunk_id": chunk_id, 
                            "text": document_text
                        },
                    }
                else:
                    existing_result["similarity_score"] = max(existing_result["similarity_score"], similarity_score)
                    existing_result["rank_position"] = min(existing_result.get("rank_position", rank_position), rank_position)

        return list(document_results.values())


