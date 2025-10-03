from pydantic import BaseModel, Field


class DeleteDocumentRequest(BaseModel):  # type: ignore[misc]
    doc_ids: list[str] = Field(...)
    collection_name: str | None = Field(default=None)


class DeleteDocumentItem(BaseModel):  # type: ignore[misc]
    doc_id: str = Field(...)
    status: str = Field(...)
    error: str | None = Field(default=None)


class DeleteDocumentResponse(BaseModel):  # type: ignore[misc]
    items: list[DeleteDocumentItem] = Field(...)
    total_documents: int = Field(...)
    successful_documents: int = Field(...)
    failed_documents: int = Field(...)
    status: str = Field(...)


class DocumentInfo(BaseModel):  # type: ignore[misc]
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    collection_name: str = Field(...)


class GetDocumentResponse(BaseModel):  # type: ignore[misc]
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    status: str = Field(...)