from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

DocKey = Tuple[str, int, int]  # (doc_id, paragraph_id, chunk_id)


@dataclass(frozen=True)
class RetrievalQuestion:
    """
    Represents a search query with both original and normalized text.
    
    Example: RetrievalQuery(original_text="log₂(x+1) = 3", 
                            normalized_text="log2(x+1) = 3")
    """
    question: str


@dataclass(frozen=True)
class EmbeddingResult:
    """
    Represents the result of text embedding with vector and status information.
    
    Example: EmbeddingResult(text="log₂(x+1) = 3", 
                            vector=[0.1, -0.2, 0.3, ...], 
                            success=True, error=None)
    """
    text: str                    # Original text that was embedded
    vector: List[float]          # Generated embedding vector
    success: bool                # Whether embedding was successful
    error: str | None = None     # Error message if embedding failed


@dataclass(frozen=True)
class VectorSearchResult:
    """
    Represents the result of vector similarity search in the vector database.
    
    Example: VectorSearchResult(query_vector=[0.1, -0.2, 0.3, ...], 
                               raw_results=[{"id": "ege_2024_task_15", "score": 0.95, "payload": {...}}], 
                               total_found=200)
    """
    query_vector: List[float]           # Vector used for the search
    raw_results: List[Dict[str, Any]]   # Raw results from vector database
    total_found: int                    # Total number of results found


@dataclass(frozen=True)
class RetrieveResult:
    """
    Represents the final result of the complete retrieve pipeline.
    
    Example: RetrieveResult(results=[{"doc_id": "ege_2024_task_15", "score": 0.95, "pages": [1, 2]}])
    """
    chunks: List[Dict[str, Any]]        # Processed retrieve results as JSON objects


@dataclass
class Candidate:
    """
    Represents a document chunk candidate with scores from different retrieval methods.
    
    Example: Candidate(key=("ege_2024_task_15", 1, 2), text="To solve log₂(x+1) = 3, we use the definition of logarithm...", 
                      pages=[1, 2], score_ann=0.95, score_bm25=0.87, score_total=0.91)
    """
    key: DocKey                          # Unique identifier (doc_id, paragraph_id, chunk_id)
    text: str                           # Text content of the chunk
    pages: List[int]                    # Page numbers where this chunk appears
    payload: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    # scores
    score_ann: float = 0.0              # Approximate Nearest Neighbor similarity score
    score_bm25: float = 0.0             # BM25 text matching score
    score_nn: float = 0.0               # Neural reranking score
    score_rrf: float = 0.0              # Reciprocal Rank Fusion score
    score_total: float = 0.0            # Final weighted combination score

    # ranks
    rank_ann: int | None = None         # Rank position in ANN results
    rank_bm25: int | None = None        # Rank position in BM25 results

    def to_json(self) -> Dict[str, Any]:
        return {
            "doc_id": self.key[0],
            "paragraph_id": self.key[1],
            "chunk_id": self.key[2],
            "text": self.text,
            "pages": self.pages,
            "score": round(float(self.score_total), 6),
        }



