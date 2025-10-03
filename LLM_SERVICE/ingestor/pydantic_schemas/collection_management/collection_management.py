from typing import List
from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):  # type: ignore[misc]
    collection_name: str | None = Field(default=None)


class ReindexResponse(BaseModel):  # type: ignore[misc]
    collection_name: str = Field(...)
    status: str = Field(...)


class SwitchAliasRequest(BaseModel):  # type: ignore[misc]
    alias_name: str = Field(default="fipi_collection")
    target_collection: str = Field(default="docs_vNext")


class SwitchAliasResponse(BaseModel):  # type: ignore[misc]
    status: str = Field(...)
    old_collection: str = Field(...)
    new_collection: str = Field(...)


class CollectionInfo(BaseModel):  # type: ignore[misc]
    name: str = Field(...)
    status: str = Field(...)
    documents: List[str] = Field(...)


class ListCollectionsResponse(BaseModel):  # type: ignore[misc]
    collections: List[CollectionInfo] = Field(...)
    total_collections: int = Field(...)
    status: str = Field(...)


    