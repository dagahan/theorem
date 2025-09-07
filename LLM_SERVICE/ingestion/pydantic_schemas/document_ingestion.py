from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class IngestDocumentRequest(BaseModel):
    doc_id: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    language: str = Field(default="en")
    text: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestDocumentResponse(BaseModel):
    job_id: str = Field(...)
    doc_id: str = Field(...)
    status: str = Field(...)


class JobStatusResponse(BaseModel):
    status: str = Field(...)
    progress: int = Field(..., ge=0, le=100)
    error: Optional[str] = Field(default=None)