from __future__ import annotations

from pydantic import BaseModel


class ContextChunk(BaseModel):  # type: ignore[misc]
    doc_id: str
    paragraph_id: int
    chunk_id: int
    text: str
    pages: list[int]
    score: float


class ContextBuilderRequest(BaseModel):  # type: ignore[misc]
    chunks: list[ContextChunk]
    max_context_chars: int
    summarizer_prompt: str


class DigestItem(BaseModel):  # type: ignore[misc]
    title: str
    summary: str
    source_chunk: ContextChunk


class ContextBuilderResponse(BaseModel):  # type: ignore[misc]
    digests: list[DigestItem]
    success: bool
    error: str | None = None


class SummarizerConfig(BaseModel):  # type: ignore[misc]
    model_name: str
    temperature: float = 0.0
    max_tokens: int = 150
    min_tokens: int = 60
    max_tokens_cap: int = 300
    chars_per_token: int = 4
    max_concurrency: int = 4


class SummarizerDigestPayload(BaseModel):  # type: ignore[misc]
    title: str
    summary: str


class SummarizerOutputPayload(BaseModel):  # type: ignore[misc]
    digests: list[SummarizerDigestPayload]


class HealthStatus(BaseModel):  # type: ignore[misc]
    status: str


