from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ContextChunk:
    doc_id: str
    paragraph_id: int
    chunk_id: int
    text: str
    pages: List[int]
    score: float


@dataclass(frozen=True)
class ContextBuilderRequest:
    chunks: List[ContextChunk]
    max_context_chars: int


@dataclass(frozen=True)
class DigestItem:
    fact: str
    doc_id: str
    paragraph_id: int
    chunk_id: int


@dataclass(frozen=True)
class EvidenceItem:
    quote: str
    doc_id: str
    paragraph_id: int
    chunk_id: int
    pages: List[int]
    score: float


@dataclass(frozen=True)
class ContextBuilderResponse:
    context_text: str
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class HealthStatus:
    status: str
    version: str