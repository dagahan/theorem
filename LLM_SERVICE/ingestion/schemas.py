"""
Pydantic models for all microservices.
"""

from .common import HealthResponse, ErrorResponse, SuccessResponse
from .document_ingestion import (
    IngestDocumentRequest,
    IngestDocumentResponse,
    JobStatusResponse,
)
from .document_management import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    DocumentInfo,
    GetDocumentResponse,
)
from .search import (
    SearchRequest,
    SearchResult,
    SearchResponse,
)
from .collection_management import (
    ReindexRequest,
    ReindexResponse,
    SwitchAliasRequest,
    SwitchAliasResponse,
    CollectionInfo,
    ListCollectionsResponse,
)
from .service_stats import (
    ServiceStats,
    StatsResponse,
)
from .ingest_files import (
    IngestFilesItem,
    IngestFilesResponse,
)

__all__ = [
    # Common
    "HealthResponse",
    "ErrorResponse", 
    "SuccessResponse",
    # Document Ingestion
    "IngestDocumentRequest",
    "IngestDocumentResponse",
    "JobStatusResponse",
    # Document Management
    "DeleteDocumentRequest",
    "DeleteDocumentResponse",
    "DocumentInfo",
    "GetDocumentResponse",
    # Search
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    # Collection Management
    "ReindexRequest",
    "ReindexResponse",
    "SwitchAliasRequest",
    "SwitchAliasResponse",
    "CollectionInfo",
    "ListCollectionsResponse",
    # Service Stats
    "ServiceStats",
    "StatsResponse",
    # File Ingestion
    "IngestFilesItem",
    "IngestFilesResponse",
]