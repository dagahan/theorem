from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, TypedDict


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HealthCheck:
    overall_status: ServiceStatus
    llm_status: ServiceStatus
    retriever_status: ServiceStatus
    embedder_status: ServiceStatus


@dataclass(frozen=True)
class UserQuery:
    raw_text: str
    stream: bool = False


@dataclass(frozen=True)
class RetrieveRequest:
    question: str
    collection_name: str


@dataclass(frozen=True)
class RetrieveResult:
    doc_id: str
    text: str
    score: float
    pages: List[int]
    paragraph_id: int = 0
    chunk_id: int = 0


@dataclass(frozen=True)
class RetrieveResponse:
    results: List[RetrieveResult]
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class QuestionBuilderRequest:
    raw_text: str


@dataclass(frozen=True)
class QuestionBuilderResponse:
    original_question: str
    expanded_question: str
    expanded_question_semantic_parts: List[str]
    success: bool
    error: Optional[str] = None


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
class ContextBuilderResponse:
    context_text: str
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class SystemPromptResponse:
    system_prompt: str
    success: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class QuestionResponse:
    answer: str
    success: bool
    error: Optional[str] = None


class GraphState(TypedDict, total=False):
    question_id: str
    started_at_ms: float
    timings_ms: Dict[str, float]

    collection_name: str
    max_context_chars: int
    min_results_required: int

    query: UserQuery

    original_question: str
    expanded_question: str
    expanded_question_semantic_parts: List[str]

    retrieval_success: bool
    retrieval_error: str
    context_chunks: List[ContextChunk]

    context_text: str
    system_prompt: str

    llm_answer: str
    llm_success: bool
    llm_error: str

    success: bool
    error: str


