from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DeleteDocumentRequest(BaseModel):
    doc_id: str = Field(...)
    collection_name: Optional[str] = Field(None)


class DeleteDocumentResponse(BaseModel):
    doc_id: str = Field(...)
    status: str = Field(...)


class DocumentInfo(BaseModel):
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    collection_name: str = Field(...)


class GetDocumentResponse(BaseModel):
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    status: str = Field(...)