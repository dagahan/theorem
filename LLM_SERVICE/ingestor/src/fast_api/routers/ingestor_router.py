from typing import List
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from loguru import logger

from pydantic_schemas import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
    DeleteDocumentsRequest,
    DeleteDocumentsItem,
    DeleteDocumentsResponse,
    IngestFilesItem,
    IngestFilesResponse,
)

from src.services.ingestor_service import IngestorService
from src.services.file_parser_service import FileParserService
from src.services.id_service import IdService


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


def get_ingestor_router(database_connector: "DataBaseConnector") -> APIRouter:
    router = APIRouter(prefix="/ingestor", tags=["documents"])
    
    file_parser_service = FileParserService()
    ingestor_service = IngestorService(database_connector)
    id_service = IdService()


    @router.post("/ingest_files", response_model=IngestFilesResponse)  # type: ignore[misc]
    async def ingest_files(
        files: List[UploadFile] = File(...),
        collection_name: str = Form(...),
        metadata: str | None = Form(None)
    ) -> IngestFilesResponse:
        try:
            parsed_metadata = json.loads(metadata) if metadata else {}
            results = []
            
            for file in files:
                try:
                    content = await file.read()

                    file_metadata = {
                        "filename": file.filename,
                        "content_type": file.content_type,
                        **parsed_metadata
                    }

                    doc_id = id_service.from_filename(file_metadata)

                    if not (file.filename.lower().endswith('.pdf') or 
                           (file.content_type and file.content_type.startswith('application/pdf'))):
                        raise ValueError("Only PDF files are supported")

                    await ingestor_service.ingest_file(
                        file_metadata=file_metadata,
                        collection_name=collection_name,
                        file_content=content
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


    @router.delete("/delete_documents", response_model=DeleteDocumentsResponse)  # type: ignore[misc]
    async def delete_documents(
        request: DeleteDocumentsRequest
    ) -> DeleteDocumentsResponse:
        try:
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
            
        except Exception as e:
            logger.error(f"Delete documents failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router


