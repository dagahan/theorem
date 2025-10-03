from pydantic import BaseModel, Field


class DeleteDocumentRequest(BaseModel):  # type: ignore[misc]
    doc_id: str = Field(...)
    collection_name: str | None = Field(default=None)


class DeleteDocumentResponse(BaseModel):  # type: ignore[misc]
    status: str = Field(...)


class DocumentInfo(BaseModel):  # type: ignore[misc]
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    collection_name: str = Field(...)


class GetDocumentResponse(BaseModel):  # type: ignore[misc]
    doc_id: str = Field(...)
    chunks_count: int = Field(...)
    status: str = Field(...)