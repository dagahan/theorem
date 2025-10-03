from typing import List, Dict, Any
from pydantic import BaseModel, Field


class Chunk(BaseModel):  # type: ignore[misc]
    id: str
    text: str
    pages: List[int]
    meta: Dict[str, Any]


class EmbeddedChunk(BaseModel):  # type: ignore[misc]
    chunk_id: str
    text: str
    vector: List[float]
    meta: Dict[str, Any]

    @property
    def success(self) -> bool:
        return len(self.vector) > 0

    @property
    def embedding_dimension(self) -> int:
        return len(self.vector)


class IngestResult(BaseModel):  # type: ignore[misc]
    filename: str
    doc_id: str
    status: str
    error: str | None


class UploadedFile(BaseModel):  # type: ignore[misc]
    filename: str
    content_type: str
    content: bytes
    meta: Dict[str, Any]

    @property
    def file_size(self) -> int:
        return len(self.content)


class IngestFilesItem(BaseModel):  # type: ignore[misc]
    filename: str = Field(...)
    doc_id: str = Field(...)
    status: str = Field(...)
    error: str | None = Field(default=None)


class IngestFilesResponse(BaseModel):  # type: ignore[misc]
    items: List[IngestFilesItem] = Field(...)
    total_files: int = Field(...)
    successful_files: int = Field(...)
    failed_files: int = Field(...)
    status: str = Field(...)


    