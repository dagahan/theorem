from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict


@dataclass(frozen=True)
class ContextChunk:
    doc_id: str
    paragraph_id: int
    chunk_id: int
    text: str
    pages: list[int]
    score: float


@dataclass(frozen=True)
class ContextBuilderRequest:
    chunks: list[ContextChunk]
    max_context_chars: int
    summarizer_prompt: str


@dataclass(frozen=True)
class DigestItem:
    title: str
    summary: str
    source_chunk: ContextChunk


@dataclass(frozen=True)
class ContextBuilderResponse:
    digests: list[DigestItem]
    success: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SummarizerConfig:
    model_name: str = field()
    temperature: float = field(default=0.0)
    max_tokens: int = field(default=150)
    min_tokens: int = field(default=60)
    max_tokens_cap: int = field(default=300)
    chars_per_token: int = field(default=4)
    max_concurrency: int = field(default=4)


class SummarizerDigestPayload(BaseModel):  # type: ignore[misc]
    model_config = ConfigDict(extra='ignore')

    title: str
    summary: str


class SummarizerOutputPayload(BaseModel):  # type: ignore[misc]
    model_config = ConfigDict(extra='ignore')

    digests: list[SummarizerDigestPayload]


@dataclass(frozen=True)
class HealthStatus:
    status: str
