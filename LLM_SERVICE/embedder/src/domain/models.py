from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EmbeddingRequest:
    text: str
    normalize: bool = True


@dataclass(frozen=True)
class EmbeddingResult:
    text: str
    vector: List[float]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class BatchEmbeddingRequest:
    texts: List[str]
    normalize: bool = True


@dataclass(frozen=True)
class BatchEmbeddingResult:
    results: List[EmbeddingResult]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class HealthStatus:
    status: str
    model_id: str
    dimensions: int




    