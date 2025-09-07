from pydantic import BaseModel, Field


class ServiceStats(BaseModel):
    total_collections: int = Field(...)
    total_vectors: int = Field(...)
    embedder_status: str = Field(...)
    qdrant_status: str = Field(...)


class StatsResponse(BaseModel):
    stats: ServiceStats = Field(...)