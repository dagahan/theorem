from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
from typing_extensions import TypedDict
from typing import Dict, Any, List


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HealthCheck:
    """
    Represents the health status of all services in the LLM Gateway.
    
    Example: HealthCheck(overall_status=ServiceStatus.HEALTHY, 
                        llm_status=ServiceStatus.HEALTHY,
                        retriever_status=ServiceStatus.HEALTHY,
                        embedder_status=ServiceStatus.HEALTHY)
    """
    overall_status: ServiceStatus      # Overall system health status
    llm_status: ServiceStatus          # LLM service health status
    retriever_status: ServiceStatus    # Retriever service health status
    embedder_status: ServiceStatus     # Embedder service health status


@dataclass(frozen=True)
class UserQuery:
    """
    Represents a user question request to the LLM Gateway.
    
    Example: QuestionRequest(question="What is the derivative of x²?", stream=False)
    """
    raw_text: str                      # User's query raw text
    stream: bool = False               # Whether to stream the response


@dataclass(frozen=True)
class RetrieveRequest:
    """
    Represents a retrieve request to the retriever service.
    
    Example: RetrieveRequest(query="logarithmic equations", collection_name="fipi_documents")
    """
    question: str                         # Retrieve query text (for backward compatibility)
    collection_name: str               # Vector database collection name


@dataclass(frozen=True)
class RetrieveResult:
    """
    Represents a single retrieve result from the retriever service.
    
    Example: RetrieveResult(doc_id="ege_2024_task_15", text="To solve log₂(x+1) = 3...", 
                         score=0.95, pages=[1, 2], paragraph_id=1, chunk_id=2)
    """
    doc_id: str                        # Document identifier
    text: str                          # Text content of the chunk
    score: float                       # Relevance score (0.0 to 1.0)
    pages: List[int]                   # Page numbers where this chunk appears
    paragraph_id: int = 0              # Paragraph identifier
    chunk_id: int = 0                  # Chunk identifier
    
    def to_json(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text": self.text,
            "score": self.score,
            "pages": self.pages,
            "paragraph_id": self.paragraph_id,
            "chunk_id": self.chunk_id
        }


@dataclass(frozen=True)
class RetrieveResponse:
    """
    Represents the response from the retriever service.
    
    Example: RetrieveResponse(results=[RetrieveResult(...)], success=True, error=None)
    """
    results: List[RetrieveResult]        # List of retrieve results
    success: bool                       # Whether the retrieve was successful
    error: Optional[str] = None        # Error message if retrieve failed


@dataclass(frozen=True)
class QuestionBuilderRequest:
    """
    Represents a request to the question builder service.
    
    Example: QuestionBuilderRequest(raw_text="реши уравнение x²-5x+6=0")
    """
    raw_text: str                  # Raw user question text


@dataclass(frozen=True)
class QuestionBuilderResponse:
    """
    Represents the response from the question builder service.
    
    Example: QuestionBuilderResponse(original_question="реши уравнение x²-5x+6=0", 
                                   expanded_question="решить квадратное уравнение x²-5x+6=0, найти корни", 
                                   semantic_parts=["найти дискриминант", "вычислить корни"], 
                                   success=True, error=None)
    """
    original_question: str                          # Normalized original question
    expanded_question: str                          # Expanded question for RAG
    expanded_question_semantic_parts: List[str]     # Semantic parts of the question
    success: bool                                   # Whether the processing was successful
    error: Optional[str] = None                     # Error message if processing failed


@dataclass(frozen=True)
class QuestionResponse:
    """
    Represents the final response from the LLM Gateway.
    
    Example: QuestionResponse(answer="The derivative of x² is 2x.", success=True, error=None)
    """
    answer: str                        # LLM generated answer
    success: bool                       # Whether the generation was successful
    error: Optional[str] = None        # Error message if generation failed


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
    context_chunks: List[Any]
    context_text: str
    llm_answer: str
    llm_success: bool
    llm_error: str
    success: bool
    error: str


class NodeResult(TypedDict, total=False):
    success: bool
    error: str
    data: Dict[str, Any]



