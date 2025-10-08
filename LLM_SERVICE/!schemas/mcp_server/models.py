from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field


class RagSearchInput(BaseModel):  # type: ignore[misc]
    query: str = Field(..., description="Search query")
    collection_name: str = Field("fipi_documents", description="Collection name")
    top_k: int = Field(6, ge=1, le=50, description="Number of results")
    max_context_chars: int = Field(8000, ge=500, le=50000)
    summarizer_prompt: str = Field("Summarize into key points, concisely")


class SourceChunk(BaseModel):  # type: ignore[misc]
    doc_id: str
    paragraph_id: int
    chunk_id: int
    text: str
    pages: List[int] = []
    score: float


class DigestItem(BaseModel):  # type: ignore[misc]
    title: str
    summary: str
    source_chunk: SourceChunk


class RagSearchOutput(BaseModel):  # type: ignore[misc]
    digests: List[DigestItem]


class HealthOutput(BaseModel):  # type: ignore[misc]
    status: Literal["ok", "degraded"]
    rag_orchestrator: str


