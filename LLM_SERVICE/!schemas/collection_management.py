from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    collection_name: Optional[str] = Field(default=None)


class ReindexResponse(BaseModel):
    collection_name: str = Field(...)
    status: str = Field(...)


class SwitchAliasRequest(BaseModel):
    alias_name: str = Field(default="docs_active")
    target_collection: str = Field(default="docs_vNext")


class SwitchAliasResponse(BaseModel):
    status: str = Field(...)
    old_collection: str = Field(...)
    new_collection: str = Field(...)


class CollectionInfo(BaseModel):
    name: str = Field(...)
    vectors_count: int = Field(...)
    config: Dict[str, Any] = Field(...)


class ListCollectionsResponse(BaseModel):
    collections: List[CollectionInfo] = Field(...)