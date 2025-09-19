from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class QuestionBuilderRequest:
    """
    Represents a request to the question builder service.
    
    Example: QuestionBuilderRequest(raw_text="реши уравнение x²-5x+6=0")
    """
    raw_text: str                      # Raw user question text


@dataclass(frozen=True)
class QuestionBuilderResponse:
    """
    Represents the response from the question builder service.
    
    Example: QuestionBuilderResponse(original_question="реши уравнение x²-5x+6=0", 
                                   expanded_question="решить квадратное уравнение x²-5x+6=0, найти корни", 
                                   expanded_question_semantic_parts=["найти дискриминант", "вычислить корни"], 
                                   success=True, error=None)
    """
    original_question: str             # Normalized original question
    expanded_question: str             # Expanded question for RAG
    expanded_question_semantic_parts: List[str]  # Semantic parts of the expanded question
    success: bool                      # Whether the processing was successful
    error: Optional[str] = None       # Error message if processing failed