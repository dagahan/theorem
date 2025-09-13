from typing import List
import json

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from loguru import logger

from pydantic_schemas import (
    DeleteDocumentRequest,
    DeleteDocumentResponse,
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

                    file_text = file_parser_service.extract_file_to_text(
                        filename=file.filename,
                        content=content,
                        content_type=file.content_type,
                        doc_id=doc_id,
                        metadata=file_metadata
                    )

                    await ingestor_service.ingest_file(
                        file_text=file_text,
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

    return router


