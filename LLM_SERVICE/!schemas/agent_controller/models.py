from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING, TypedDict

from pydantic import BaseModel

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


class ComponentHealth(BaseModel):  # type: ignore[misc]
    name: str
    status: ServiceStatus
    details: str | None = None


class HealthCheck(BaseModel):  # type: ignore[misc]
    overall_status: ServiceStatus
    components: list[ComponentHealth]


class UserQuery(BaseModel):  # type: ignore[misc]
    raw_text: str
    agent_name: str
    stream: bool = False


class RetrieveRequest(BaseModel):  # type: ignore[misc]
    question: str
    collection_name: str


class RetrieveResult(BaseModel):  # type: ignore[misc]
    doc_id: str
    text: str
    score: float
    pages: list[int]
    paragraph_id: int = 0
    chunk_id: int = 0


class RetrieveResponse(BaseModel):  # type: ignore[misc]
    results: list[RetrieveResult]
    success: bool
    error: str | None = None


class QuestionBuilderRequest(BaseModel):  # type: ignore[misc]
    raw_text: str


class QuestionBuilderResponse(BaseModel):  # type: ignore[misc]
    original_question: str
    expanded_question: str
    expanded_question_semantic_parts: list[str]
    success: bool
    error: str | None = None


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


class ContextDigestItem(BaseModel):  # type: ignore[misc]
    title: str
    summary: str
    source_chunk: ContextChunk


class ContextBuilderResponse(BaseModel):  # type: ignore[misc]
    digests: list[ContextDigestItem]
    success: bool
    error: str | None = None


class SystemPromptResponse(BaseModel):  # type: ignore[misc]
    personalities: dict[str, str]
    success: bool
    error: str | None = None


class QuestionResponse(BaseModel):  # type: ignore[misc]
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


class StepSpec(BaseModel):  # type: ignore[misc]
    name: str
    handler: NodeHandler
    success_key: str
    on_fail: str = "failure"


class GraphNodeFactory(BaseModel):  # type: ignore[misc]
    system_prompt_builder_node: SystemPromptBuilderNode
    question_builder_node: QuestionBuilderNode
    retrieval_node: RetrievalNode
    context_builder_node: ContextBuilderNode
    llm_generation_node: LLMGenerationNode


class ResponderConfig(BaseModel):  # type: ignore[misc]
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 800


class ResponderRuntime(BaseModel):  # type: ignore[misc]
    system_prompt: str
    question: str
    context: str
    agent_name: str
    stream: bool



