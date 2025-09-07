from typing import Any, Dict, List, Optional
import json
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks, status, UploadFile, File, Form
from loguru import logger

from pydantic_schemas import (
    IngestDocumentRequest,
    IngestDocumentResponse,
    SearchRequest,
    SearchResult,
    SearchResponse,
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    CollectionInfo,
    ListCollectionsResponse,
    DocumentInfo,
    GetDocumentResponse,
    ServiceStats,
    StatsResponse,
    IngestFilesItem,
    IngestFilesResponse,
)

from src.services.ingestion_service import IngestionService
from src.services.file_text_extractor import FileTextExtractor


def _get_ingestion_service() -> IngestionService:
    return IngestionService()


def get_ingestion_router() -> APIRouter:
    router = APIRouter(prefix="/ingestion", tags=["ingestion"])
    extractor = FileTextExtractor()


    @router.post("/ingest", response_model=IngestDocumentResponse, status_code=202)  # type: ignore[misc]
    async def ingest_document(
        request: IngestDocumentRequest,  # noqa: F821
        background_tasks: BackgroundTasks,
    ) -> IngestDocumentResponse:

        try:
            ingestion_service = _get_ingestion_service()
            doc_id = request.doc_id or str(uuid.uuid4())
            background_tasks.add_task(
                ingestion_service._process_document,
                doc_id,
                request.text,
                request.metadata
            )

            return IngestDocumentResponse(job_id=doc_id, doc_id=doc_id, status="processing")

        except Exception as e:
            logger.error(f"Failed to queue document ingestion: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to queue document ingestion: {str(e)}")


    @router.post("/ingest-files", response_model=IngestFilesResponse, status_code=202)  # type: ignore[misc]
    async def ingest_files(
        background_tasks: BackgroundTasks,            
        files: List[UploadFile] = File(...),
        language: str = Form("en"),
        metadata: Optional[str] = Form(None),
    ) -> IngestFilesResponse:
        try:
            ingestion_service = _get_ingestion_service()

            meta: Dict[str, Any] = {}
            if metadata:
                try:
                    meta = json.loads(metadata)
                    if not isinstance(meta, dict):
                        meta = {}
                except Exception:
                    meta = {}

            items: List[IngestFilesItem] = []

            if not files:
                raise HTTPException(status_code=400, detail="no files provided")

            for f in files:
                try:
                    content = await f.read()
                    text = extractor.extract(f.filename or "file", content, f.content_type or "")

                    if not text or not text.strip():
                        raise ValueError("empty text after extraction")

                    doc_id = str(uuid.uuid4())
                    meta_all = {
                        **meta,
                        "filename": f.filename,
                        "content_type": f.content_type,
                        "language": language,
                    }

                    background_tasks.add_task(
                        ingestion_service._process_document,
                        doc_id,
                        text,
                        meta_all,
                    )

                    items.append(IngestFilesItem(job_id=doc_id, doc_id=doc_id, status="processing"))

                except Exception as ex:
                    logger.exception(f"file '{getattr(f, 'filename', '<unknown>')}' failed: {ex}")

            return IngestFilesResponse(items=items, total=len(items))

        except HTTPException:
            raise
        
        except Exception as e:
            logger.error(f"ingest-files failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


    @router.post("/search", response_model=SearchResponse)  # type: ignore[misc]
    async def search_documents(request: SearchRequest) -> SearchResponse:
        ingestion_service = _get_ingestion_service()
        ctx = await ingestion_service.orchestrator.search_with_context(
            query=request.query,
            collection_name=request.collection_name or ingestion_service.collection_name,
            top_k=request.limit,
            neighbor_window=request.neighbor_window if hasattr(request, "neighbor_window") else 2,
            include_whole_paragraph=request.include_whole_paragraph if hasattr(request, "include_whole_paragraph") else True,
        )

        results: List[SearchResult] = []

        for item in ctx["chunks"]:
            p = item["payload"]
            results.append(SearchResult(
                id=str(item["id"]),
                score=0.0,
                text=p.get("text", ""),
                doc_id=p.get("doc_id", ""),
                paragraph_id=int(p.get("paragraph_id", 0)),
                chunk_id=int(p.get("chunk_id", 0)),
                metadata=p.get("metadata", {}),
            ))

        return SearchResponse(results=results, total=len(results), query=request.query, merged_text=ctx["merged_text"])


    @router.delete("/document", response_model=DeleteDocumentResponse)  # type: ignore[misc]
    async def delete_document(request: DeleteDocumentRequest) -> DeleteDocumentResponse:
        ingestion_service = _get_ingestion_service()

        await ingestion_service.delete_document(request.doc_id)

        return DeleteDocumentResponse(doc_id=request.doc_id, status="deleted")


    @router.get("/document/{doc_id}", response_model=GetDocumentResponse)  # type: ignore[misc]
    async def get_document_info(
        doc_id: str,
        collection_name: Optional[str] = None
    ) -> GetDocumentResponse:

        ingestion_service = _get_ingestion_service()
        collection_name = collection_name or ingestion_service.collection_name
        count = await ingestion_service.orchestrator.vector_store_service.get_document_chunks_count(collection_name, doc_id)

        return GetDocumentResponse(document=DocumentInfo(doc_id=doc_id, chunks_count=count, collection_name=collection_name))


    @router.get("/stats", response_model=StatsResponse)  # type: ignore[misc]
    async def get_service_stats() -> StatsResponse:
        ingestion_service = _get_ingestion_service()
        stats = await ingestion_service.get_service_stats()

        return StatsResponse(stats=ServiceStats(
            total_collections=stats["total_collections"],
            total_vectors=stats["total_vectors"],
            embedder_status=stats["embedder_status"],
            qdrant_status=stats["qdrant_status"],
        ))


    @router.get("/health")  # type: ignore[misc]
    async def health_check() -> Dict[str, str]:
        ingestion_service = _get_ingestion_service()

        return await ingestion_service.health_check()


    @router.get("/collections", response_model=ListCollectionsResponse)  # type: ignore[misc]
    async def list_collections() -> ListCollectionsResponse:
        ingestion_service = _get_ingestion_service()
        cols = await ingestion_service.orchestrator.vector_store_service.get_collections()
        infos = [CollectionInfo(name=c["name"], vectors_count=c["vectors_count"], config=c["config"]) for c in cols]

        return ListCollectionsResponse(collections=infos)



    return router


