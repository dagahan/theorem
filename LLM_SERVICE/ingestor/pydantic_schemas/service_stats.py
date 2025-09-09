from pydantic import BaseModel, Field


class ServiceStats(BaseModel):
    total_collections: int = Field(default=0)
    total_vectors: int = Field(default=0)
    embedder_status: str = Field(default="unknown")
    qdrant_status: str = Field(default="unknown")
    error_message: str = Field(default="")

