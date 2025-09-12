from pydantic import BaseModel, Field


class ServiceStats(BaseModel):
    total_collections: int = Field(default=0)
    total_vectors: int = Field(default=0)
    embedder_status: str = Field(default="unknown")
    embedder_model_id: str = Field(default="")
    embedder_dim: int = Field(default=0)
    qdrant_status: str = Field(default="unknown")
    error_message: str = Field(default="")

