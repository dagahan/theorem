from pydantic import BaseModel, Field


class ServiceStats(BaseModel):
    total_collections: int = Field(...)
    total_vectors: int = Field(...)

