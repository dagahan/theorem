from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from src.agents_graphs.nodes.context_builder_node import ContextBuilderNode
    from src.agents_graphs.nodes.llm_generation_node import LLMGenerationNode
    from src.agents_graphs.nodes.question_builder_node import QuestionBuilderNode
    from src.agents_graphs.nodes.retrieval_node import RetrievalNode
    from src.agents_graphs.nodes.system_prompt_builder_node import SystemPromptBuilderNode


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: ServiceStatus
    details: str | None = None


@dataclass(frozen=True)
class HealthCheck:
    overall_status: ServiceStatus
    components: list[ComponentHealth]


@dataclass(frozen=True)
class UserQuery:
    raw_text: str
    agent_name: str
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
    pages: list[int]
    paragraph_id: int = 0
    chunk_id: int = 0


@dataclass(frozen=True)
class RetrieveResponse:
    results: list[RetrieveResult]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class QuestionBuilderRequest:
    raw_text: str


@dataclass(frozen=True)
class QuestionBuilderResponse:
    original_question: str
    expanded_question: str
    expanded_question_semantic_parts: list[str]
    success: bool
    error: str | None = None


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
class ContextDigestItem:
    title: str
    summary: str
    source_chunk: ContextChunk


@dataclass(frozen=True)
class ContextBuilderResponse:
    digests: list[ContextDigestItem]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class SystemPromptResponse:
    personalities: dict[str, str]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class QuestionResponse:
    answer: str
    success: bool
    error: str | None = None


class GraphState(TypedDict, total=False):
    question_id: str
    started_at_ms: float
    timings_ms: dict[str, float]

    collection_name: str
    max_context_chars: int
    min_results_required: int

    query: UserQuery
    agent_name: str

    original_question: str
    expanded_question: str
    expanded_question_semantic_parts: list[str]

    retrieval_success: bool
    retrieval_error: str
    context_chunks: list[ContextChunk]

    context_digests: list[ContextDigestItem]
    personality_prompts: dict[str, str]
    system_prompt: str

    llm_answer: str
    llm_success: bool
    llm_error: str

    success: bool
    error: str


NodeHandler = Callable[[GraphState], Awaitable[GraphState]]


@dataclass(frozen=True)
class StepSpec:
    name: str
    handler: NodeHandler
    success_key: str
    on_fail: str = 'failure'


@dataclass(frozen=True)
class GraphNodeFactory:
    system_prompt_builder_node: SystemPromptBuilderNode
    question_builder_node: QuestionBuilderNode
    retrieval_node: RetrievalNode
    context_builder_node: ContextBuilderNode
    llm_generation_node: LLMGenerationNode


@dataclass(frozen=True)
class ResponderConfig:
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 800


@dataclass(frozen=True)
class ResponderRuntime:
    system_prompt: str
    question: str
    context: str
    agent_name: str
    stream: bool
