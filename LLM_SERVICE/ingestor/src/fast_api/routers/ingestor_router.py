from typing import Any, Dict, List, Optional
import json
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks, status, UploadFile, File, Form
from loguru import logger

from pydantic_schemas import (
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
    HealthResponse,
    IngestFilesItem,
    IngestFilesResponse,
)

from src.services.ingestor_service import IngestorService
from src.services.file_text_extractor import FileTextExtractor


def get_ingestor_router() -> APIRouter:
    router = APIRouter(prefix="/ingestor", tags=["ingestor"])
    extractor = FileTextExtractor()
    ingestor_service = IngestorService()


    @router.get("/health", response_model=HealthResponse)  # type: ignore[misc]
    async def health_check() -> HealthResponse:
        return HealthResponse(
            status="healthy"
        )


    @router.get("/get_document_info/{doc_id}", response_model=GetDocumentResponse)  # type: ignore[misc]
    async def get_document_info(
        doc_id: str,
        collection_name: Optional[str] = None
    ) -> GetDocumentResponse:
        try:
            chunks_count = await ingestor_service.get_document_chunks_count(doc_id, collection_name)
            return GetDocumentResponse(
                doc_id=doc_id,
                chunks_count=chunks_count,
                status="success"
            )
        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.post("/search", response_model=SearchResponse)  # type: ignore[misc]
    async def search_documents(
        request: SearchRequest,
        background_tasks: BackgroundTasks
    ) -> SearchResponse:
        try:
            results = await ingestor_service.search_documents(
                query=request.query,
                collection_name=request.collection_name,
                limit=request.limit,
                score_threshold=request.score_threshold
            )
            
            search_results = [
                SearchResult(
                    doc_id=result["payload"]["doc_id"],
                    paragraph_id=result["payload"]["paragraph_id"],
                    chunk_id=result["payload"]["chunk_id"],
                    text=result["payload"]["text"],
                    score=result["score"],
                    metadata=result["payload"]["metadata"]
                )
                for result in results
            ]
            
            return SearchResponse(
                results=search_results,
                total_results=len(search_results),
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.post("/search_with_context", response_model=Dict[str, Any])  # type: ignore[misc]
    async def search_with_context(
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 25,
        neighbor_window: int = 2,
        include_whole_paragraph: bool = True
    ) -> Dict[str, Any]:
        try:
            result = await ingestor_service.search_with_context(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                neighbor_window=neighbor_window,
                include_whole_paragraph=include_whole_paragraph
            )
            return result
            
        except Exception as e:
            logger.error(f"Search with context failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.delete("/delete_document", response_model=DeleteDocumentResponse)  # type: ignore[misc]
    async def delete_document(
        request: DeleteDocumentRequest
    ) -> DeleteDocumentResponse:
        try:
            result = await ingestor_service.delete_document(
                doc_id=request.doc_id,
                collection_name=request.collection_name
            )
            return DeleteDocumentResponse(
                doc_id=request.doc_id,
                status=result["status"]
            )
            
        except Exception as e:
            logger.error(f"Delete document failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.get("/list_collections", response_model=ListCollectionsResponse)  # type: ignore[misc]
    async def list_collections() -> ListCollectionsResponse:
        try:
            collections = await ingestor_service.list_collections()
            collection_infos = [
                CollectionInfo(name=name, status="active")
                for name in collections
            ]
            return ListCollectionsResponse(
                collections=collection_infos,
                total_collections=len(collection_infos),
                status="success"
            )
            
        except Exception as e:
            logger.error(f"List collections failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.post("/ingest_files", response_model=IngestFilesResponse)  # type: ignore[misc]
    async def ingest_files(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
        collection_name: Optional[str] = Form(None),
        metadata: Optional[str] = Form(None)
    ) -> IngestFilesResponse:
        try:
            parsed_metadata = json.loads(metadata) if metadata else {}
            results = []
            
            for file in files:
                try:
                    doc_id = str(uuid.uuid4())
                    content = await file.read()
                    text = extractor.extract(file.filename, content, file.content_type)
                    
                    file_metadata = {
                        "filename": file.filename,
                        "content_type": file.content_type,
                        **parsed_metadata
                    }
                    
                    await ingestor_service.ingest_document(
                        doc_id=doc_id,
                        text=text,
                        metadata=file_metadata,
                        collection_name=collection_name
                    )
                    
                    results.append(IngestFilesItem(
                        filename=file.filename,
                        doc_id=doc_id,
                        status="success"
                    ))
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file.filename}: {e}")
                    results.append(IngestFilesItem(
                        filename=file.filename,
                        doc_id="",
                        status="failed",
                        error=str(e)
                    ))
            
            return IngestFilesResponse(
                items=results,
                total_files=len(results),
                successful_files=len([r for r in results if r.status == "success"]),
                failed_files=len([r for r in results if r.status == "failed"]),
                status="completed"
            )
            
        except Exception as e:
            logger.error(f"Ingest files failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.get("/service_stats", response_model=ServiceStats)  # type: ignore[misc]
    async def get_service_stats() -> ServiceStats:
        try:
            stats = await ingestor_service.get_service_stats()
            return stats
            
        except Exception as e:
            logger.error(f"Get service stats failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    return router


    