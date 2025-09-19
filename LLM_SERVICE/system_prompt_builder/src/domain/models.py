from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class QuestionType(Enum):
    ALGEBRAIC = "algebraic"
    GEOMETRIC = "geometric"
    TRIGONOMETRIC = "trigonometric"
    CALCULUS = "calculus"
    STATISTICS = "statistics"
    GENERAL = "general"


class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True)
class SystemPromptRequest:
    """
    Represents a request to build system prompt.
    
    Example: SystemPromptRequest(question="реши уравнение x²-5x+6=0", 
                               context_text="RETRIEVER_CONTEXT_START...", 
                               question_type=QuestionType.ALGEBRAIC, 
                               difficulty=DifficultyLevel.MEDIUM)
    """
    question: str
    context_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    streaming: bool = False


@dataclass(frozen=True)
class PolicyHeader:
    """
    Represents policy configuration for LLM.
    
    Example: PolicyHeader(role="Mathematics Tutor", tone="educational", 
                        temperature=0.7, max_tokens=2048, 
                        stop_sequences=["END", "STOP"])
    """
    role: str
    tone: str
    temperature: float
    max_tokens: int
    stop_sequences: List[str]


@dataclass(frozen=True)
class BudgetEstimate:
    """
    Represents token budget estimation.
    
    Example: BudgetEstimate(max_tokens=2048, context_ratio=0.6, 
                          ttfb_budget_ms=2000, ttl_budget_ms=30000)
    """
    max_tokens: int
    context_ratio: float
    ttfb_budget_ms: int
    ttl_budget_ms: int


@dataclass(frozen=True)
class SystemPromptResponse:
    """
    Represents the complete system prompt response.
    
    Example: SystemPromptResponse(system_prompt="You are a mathematics tutor...", 
                                policy_header=PolicyHeader(...), 
                                budget_estimate=BudgetEstimate(...), 
                                success=True, error=None)
    """
    system_prompt: str
    policy_header: PolicyHeader
    budget_estimate: BudgetEstimate
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class HealthStatus:
    """
    Represents the health status of the system prompt builder service.
    
    Example: HealthStatus(status="healthy", version="0.0.1")
    """
    status: str
    version: str