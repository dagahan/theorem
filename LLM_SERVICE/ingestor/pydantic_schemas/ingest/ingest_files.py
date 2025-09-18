from typing import List
from pydantic import BaseModel, Field


class IngestResult(BaseModel):
    filename: str = Field(...)
    doc_id: str = Field(...)
    status: str = Field(...)
    error: str | None = Field(default=None)


class IngestFilesResponse(BaseModel):
    items: List[IngestResult] = Field(...)
    total_files: int = Field(...)
    successful_files: int = Field(...)
    failed_files: int = Field(...)
    status: str = Field(...)


    