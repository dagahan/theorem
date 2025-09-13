from typing import Any, Dict, List
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=25, ge=1, le=100)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    collection_name: str | None = Field(default=None)
    neighbor_window: int = Field(default=2, ge=0, le=10)
    include_whole_paragraph: bool = Field(default=True)


class SearchWithContextRequest(BaseModel):
    query: str = Field(..., min_length=1)
    collection_name: str | None = Field(default=None)
    top_k: int = Field(default=25, ge=1, le=100)
    neighbor_window: int = Field(default=2, ge=0, le=10)
    include_whole_paragraph: bool = Field(default=True)


class SearchResult(BaseModel):
    id: str
    score: float
    text: str
    doc_id: str
    paragraph_id: int
    chunk_id: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    merged_text: str

