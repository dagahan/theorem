from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class QuestionBuilderRequest(BaseModel):  # type: ignore[misc]
    raw_text: str


class QuestionBuilderResponse(BaseModel):  # type: ignore[misc]
    original_question: str
    expanded_question: str
    expanded_question_semantic_parts: List[str]
    success: bool
    error: Optional[str] = None



