from typing import List, Optional
from pydantic import BaseModel, Field


class IngestFilesItem(BaseModel):
    filename: str = Field(...)
    doc_id: str = Field(...)
    status: str = Field(...)
    error: Optional[str] = Field(default=None)


class IngestFilesResponse(BaseModel):
    items: List[IngestFilesItem] = Field(...)
    total_files: int = Field(...)
    successful_files: int = Field(...)
    failed_files: int = Field(...)
    status: str = Field(...)


    