from __future__ import annotations

from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TYPE_CHECKING, TypedDict, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.agents_graphs.nodes.context_builder_node import ContextBuilderNode
    from src.agents_graphs.nodes.response_answer_node import ResponseAnswerNode
    from src.agents_graphs.nodes.question_builder_node import QuestionBuilderNode
    from src.agents_graphs.nodes.retrieval_node import RetrievalNode
    from src.agents_graphs.nodes.personality_builder_node import PersonalityBuilderNode


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
    question: str
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


class Personality(BaseModel):  # type: ignore[misc]
    name: str
    system_prompt: str
    response_schema: Any | None = None


class Personalities(BaseModel):  # type: ignore[misc]
    personalities: dict[str, Personality]


class PersonalityResponse(BaseModel):  # type: ignore[misc]
    personalities: list[Any]
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

    question: str

    retrieval_success: bool
    retrieval_error: str
    context_chunks: list[ContextChunk]

    context_digests: list[ContextDigestItem]
    personalities: Personalities

    inference_params: InferenceParams

    response_answer: str
    response_success: bool
    response_error: str

    success: bool
    error: str


NodeHandler = Callable[[GraphState], Awaitable[GraphState]]


class StepSpec(BaseModel):  # type: ignore[misc]
    name: str
    handler: NodeHandler
    success_key: str
    on_fail: str = "failure"


class InferenceParams(BaseModel):  # type: ignore[misc]
    temperature: float = 0.2
    max_tokens: int = 800
    model_name: str = "vllm"


class GraphNodeFactory(BaseModel):  # type: ignore[misc]
    personality_builder_node: PersonalityBuilderNode
    question_builder_node: QuestionBuilderNode
    retrieval_node: RetrievalNode
    context_builder_node: ContextBuilderNode
    response_answer_node: ResponseAnswerNode



