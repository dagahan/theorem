from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class HealthStatus(BaseModel):  # type: ignore[misc]
    status: str
    model_id: str
    dimensions: int
    sparse_vocab_size: int


class DenseEmbedRequest(BaseModel):  # type: ignore[misc]
    text: str


class DenseEmbedResponse(BaseModel):  # type: ignore[misc]
    vector: List[float]
    success: bool
    error: Optional[str] = None


class DenseEmbedBatchRequest(BaseModel):  # type: ignore[misc]
    texts: List[str]


class DenseEmbedBatchResponse(BaseModel):  # type: ignore[misc]
    items: List[DenseEmbedResponse]
    success: bool
    error: Optional[str] = None


class SparseEmbedRequest(BaseModel):  # type: ignore[misc]
    text: str


class SparseEmbedResponse(BaseModel):  # type: ignore[misc]
    indices: List[int]
    values: List[float]
    success: bool
    error: Optional[str] = None


class SparseEmbedBatchRequest(BaseModel):  # type: ignore[misc]
    texts: List[str]


class SparseEmbedBatchResponse(BaseModel):  # type: ignore[misc]
    items: List[SparseEmbedResponse]
    success: bool
    error: Optional[str] = None
