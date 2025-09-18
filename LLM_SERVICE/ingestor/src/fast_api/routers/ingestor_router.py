from typing import List
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from loguru import logger

from pydantic_schemas import (
    DeleteDocumentsRequest,
    DeleteDocumentsItem,
    DeleteDocumentsResponse,
    IngestFilesResponse,
    IngestResult as PydanticIngestResult,
)

from src.services.ingestor_service import IngestorService
from src.services.health_service import HealthService


from typing import TYPE_CHECKING, List, Dict, Any
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector
    from src.data_classes.data_classes import IngestResult


def get_ingestor_router(database_connector: "DataBaseConnector") -> APIRouter:
    router = APIRouter(prefix="/ingestor", tags=["documents"])
    
    ingestor_service = IngestorService(database_connector)
    health_service = HealthService(database_connector)


    @router.post("/ingest_files", response_model=IngestFilesResponse)  # type: ignore[misc]
    async def ingest_files(
        files: List[UploadFile] = File(...),
        collection_name: str = Form(...),
        metadata: str | None = Form(None)
    ) -> IngestFilesResponse:
        try:
            await health_service.ensure_all_healthy()
            
            parsed_metadata: Dict[str, Any] = json.loads(metadata) if metadata else {}
            
            allowed_metadata_fields = {"filename"}
            
            filtered_metadata = {
                k: v for k, v in parsed_metadata.items() 
                if k in allowed_metadata_fields
            }
            
            ingest_results: List[IngestResult] = await ingestor_service.ingest_files(
                files=files,
                collection_name=collection_name,
                metadata=filtered_metadata
            )
            
            successful_count: int = len([r for r in ingest_results if r.status == "success"])

            failed_count: int = len([r for r in ingest_results if r.status == "failed"])
            
            pydantic_ingest_results = [
                PydanticIngestResult(
                    filename=result.filename,
                    doc_id=result.doc_id,
                    status=result.status,
                    error=result.error
                )
                for result in ingest_results
            ]
            
            return IngestFilesResponse(
                items=pydantic_ingest_results,
                total_files=len(ingest_results),
                successful_files=successful_count,
                failed_files=failed_count,
                status="completed"
            )
            
        except Exception as ex:
            logger.error(f"Ingest files failed: {ex}")
            raise HTTPException(status_code=500, detail=str(ex))


    @router.delete("/delete_documents", response_model=DeleteDocumentsResponse)  # type: ignore[misc]
    async def delete_documents(
        request: DeleteDocumentsRequest
    ) -> DeleteDocumentsResponse:
        try:
            await health_service.ensure_all_healthy()
            
            results = await ingestor_service.delete_documents(
                doc_ids=request.doc_ids,
                collection_name=request.collection_name
            )
            
            items = [
                DeleteDocumentsItem(
                    doc_id=result["doc_id"],
                    status=result["status"],
                    error=result.get("error")
                )
                for result in results
            ]
            
            successful_count = len([item for item in items if item.status == "deleted"])
            failed_count = len([item for item in items if item.status != "deleted"])
            
            return DeleteDocumentsResponse(
                items=items,
                total_documents=len(items),
                successful_documents=successful_count,
                failed_documents=failed_count,
                status="completed"
            )
            
        except Exception as ex:
            logger.error(f"Delete documents failed: {ex}")
            raise HTTPException(status_code=500, detail=str(ex))

    return router


