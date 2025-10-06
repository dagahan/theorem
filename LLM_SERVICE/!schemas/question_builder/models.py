from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class QuestionBuilderRequest(BaseModel):  # type: ignore[misc]
    raw_text: str


class QuestionBuilderResponse(BaseModel):  # type: ignore[misc]
    question: str
    success: bool
    error: Optional[str] = None



