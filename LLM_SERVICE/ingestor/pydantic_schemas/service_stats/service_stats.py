from pydantic import BaseModel, Field


class ServiceStats(BaseModel):  # type: ignore[misc]
    total_collections: int = Field(default=0)
    total_vectors: int = Field(default=0)
    hybrid_embedder_status: str = Field(default="unknown")
    hybrid_embedder_model_id: str = Field(default="")
    hybrid_embedder_dim: int = Field(default=0)
    qdrant_status: str = Field(default="unknown")
    error_message: str = Field(default="")
