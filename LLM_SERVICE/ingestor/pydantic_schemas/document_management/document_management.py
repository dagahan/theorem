from typing import Any, Dict
from pydantic import BaseModel, Field


class DeleteDocumentsRequest(BaseModel):
    doc_ids: list[str] = Field(...)
    collection_name: str | None = Field(default=None)


class DeleteDocumentsItem(BaseModel):
    doc_id: str = Field(...)
    status: str = Field(...)
    error: str | None = Field(default=None)


class DeleteDocumentsResponse(BaseModel):
    items: list[DeleteDocumentsItem] = Field(...)
    total_documents: int = Field(...)
    successful_documents: int = Field(...)
    failed_documents: int = Field(...)
    status: str = Field(...)


class DocumentInfo(BaseModel):
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    collection_name: str = Field(...)


class GetDocumentResponse(BaseModel):
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    status: str = Field(...)