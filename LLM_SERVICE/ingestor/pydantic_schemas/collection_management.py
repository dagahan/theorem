from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    collection_name: Optional[str] = Field(default=None)


class ReindexResponse(BaseModel):
    collection_name: str = Field(...)
    status: str = Field(...)


class SwitchAliasRequest(BaseModel):
    alias_name: str = Field(default="fipi_collection")
    target_collection: str = Field(default="docs_vNext")


class SwitchAliasResponse(BaseModel):
    status: str = Field(...)
    old_collection: str = Field(...)
    new_collection: str = Field(...)


class CollectionInfo(BaseModel):
    name: str = Field(...)
    status: str = Field(...)
    documents: List[str] = Field(default_factory=list)


class ListCollectionsResponse(BaseModel):
    collections: List[CollectionInfo] = Field(...)