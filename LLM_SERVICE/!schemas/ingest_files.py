from typing import List
from pydantic import BaseModel, Field


class IngestFilesItem(BaseModel):
    job_id: str = Field(...)
    doc_id: str = Field(...)
    status: str = Field(...)


class IngestFilesResponse(BaseModel):
    items: List[IngestFilesItem] = Field(...)
    total: int = Field(...)


    