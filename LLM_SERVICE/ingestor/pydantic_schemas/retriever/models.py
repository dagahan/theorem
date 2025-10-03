from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

DocKey = Tuple[str, int, int]


class RetrievalQuestion(BaseModel):  # type: ignore[misc]
    question: str


class EmbeddingResult(BaseModel):  # type: ignore[misc]
    text: str
    vector: List[float]
    success: bool
    error: str | None = None


class VectorSearchResult(BaseModel):  # type: ignore[misc]
    query_vector: List[float]
    raw_results: List[Dict[str, Any]]
    total_found: int


class RetrieveResult(BaseModel):  # type: ignore[misc]
    chunks: List[Dict[str, Any]]


class Candidate(BaseModel):  # type: ignore[misc]
    key: DocKey
    text: str
    pages: List[int]
    payload: Dict[str, Any] = Field(default_factory=dict)

    score_ann: float = 0.0
    score_bm25: float = 0.0
    score_nn: float = 0.0
    score_rrf: float = 0.0
    score_total: float = 0.0

    rank_ann: int | None = None
    rank_bm25: int | None = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "doc_id": self.key[0],
            "paragraph_id": self.key[1],
            "chunk_id": self.key[2],
            "text": self.text,
            "pages": self.pages,
            "score": round(float(self.score_total), 6),
        }


