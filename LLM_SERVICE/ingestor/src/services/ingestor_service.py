from __future__ import annotations
from typing import List, Dict, Any, Union
import re
from loguru import logger

from src.data_classes.data_classes import PdfFile, IngestResult
from src.services.chunking_service import ChunkingService
from src.services.document_service import DocumentService
from src.services.text_normalize_service import TextNormalizeService
from src.services.health_service import HealthService
from src.services.vector_store_service import VectorStoreService
from src.services.statistics_service import StatisticsService
from src.services.id_service import IdService
from src.services.file_parser_service import FileParserService
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.transaction_manager.transaction_manager import transactional, execute_atomic_step

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector
    from qdrant_client.http import models as qm
    from pydantic_schemas import Document
    from src.data_classes.data_classes import Block, Chunk, EmbeddedChunk


class IngestorService:
    def __init__(self, database_connector: "DataBaseConnector") -> None:
        self.chunking_service = ChunkingService()
        self.document_service = DocumentService()
        self.text_normalize_service = TextNormalizeService()
        self.health_service = HealthService(database_connector)
        self.vector_store_service = VectorStoreService()
        self.statistics_service = StatisticsService(database_connector)
        self.file_parser_service = FileParserService()
        self.db_connector = database_connector
        self.embedder_grpc_client = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)

    
    async def ingest_files(
        self,
        files: List[Any],
        collection_name: str,
        metadata: Dict[str, Any]
    ) -> List[IngestResult]:
        """
        Processes multiple files through the ingestion pipeline.
        Validates each file type and creates appropriate dataclass objects.
        """
        results = []
        
        for file in files:
            try:
                content = await file.read()
                
                if not (file.filename.lower().endswith('.pdf') or 
                       (file.content_type and file.content_type.startswith('application/pdf'))):
                    raise ValueError("Only PDF files are supported")
                
                pdf_file = PdfFile(
                    filename=file.filename,
                    content_type=file.content_type or "application/pdf",
                    content=content,
                    meta={**metadata}
                )
                
                await self.ingest_file(
                    pdf_file=pdf_file,
                    collection_name=collection_name
                )
                
                results.append(IngestResult(
                    filename=file.filename,
                    doc_id=pdf_file.doc_id,
                    status="success",
                    error=None
                ))
                
            except Exception as ex:
                logger.error(f"Failed to process file {file.filename}: {ex}")
                results.append(IngestResult(
                    filename=file.filename,
                    doc_id="",
                    status="failed",
                    error=str(ex)
                ))
        
        return results


    @transactional
    async def ingest_file(
        self,
        pdf_file: PdfFile,
        collection_name: str,
    ) -> None:
        """
        Processes a PDF file through the complete ingestion pipeline with automatic rollback.
        """
        doc_id: str = IdService.make_id_by_filename(pdf_file.meta)

        await self.vector_store_service.ensure_collection_exists(collection_name)

        if await self.vector_store_service.is_document_exists(collection_name, doc_id):
            raise ValueError(f"Document with id '{doc_id}' already exists in collection '{collection_name}'. "
                             f"File name (without extension) must be unique.")
            
        s3_uploaded_key: str = await execute_atomic_step(
            action=lambda: self.document_service.required_upload_file_to_s3(
                pdf=pdf_file,
                collection_name=collection_name
            ),
            rollback=lambda s3_uploaded_key: self._rollback_s3_upload(s3_uploaded_key)
        )
        
        blocks: List["Block"] = self.file_parser_service.extract_blocks_from_pdf(pdf_file)

        chunks: List["Chunk"] = self.chunking_service.chunk_blocks(
            doc_id, blocks,
            pdf_file.meta
        )

        embedded_chunks: List["EmbeddedChunk"] = await self.embedder_grpc_client.embed_chunks(chunks)

        point_structs: List[qm.PointStruct] = self.vector_store_service.build_point_structs_from_embedded_chunks(
            embedded_chunks,
            doc_id,
            pdf_file.meta
        )

        await execute_atomic_step(
            action=lambda: self.vector_store_service.upsert_batched_to_collection(
                collection_name,
                point_structs
            ),
            rollback=lambda _: self.vector_store_service.delete_document(
                doc_id,
                collection_name
            )
        )
        
        await execute_atomic_step(
            action=lambda: self._create_db_record(
                doc_id,
                pdf_file,
                s3_uploaded_key,
                collection_name
            ),
            rollback=lambda record: self._rollback_db_record(
                record,
                doc_id
            )
        )
        
        logger.info(f"Document {doc_id} successfully ingested with {len(chunks)} chunks" + 
                   (f" and stored in S3: {s3_uploaded_key}" if s3_uploaded_key else ""))


    async def _rollback_s3_upload(
        self,
        s3_uploaded_key: str
    ) -> None:
        await self.document_service.delete_file_from_s3(s3_uploaded_key)


    async def _create_db_record(
        self, 
        doc_id: str, 
        pdf_file: PdfFile, 
        s3_uploaded_key: str, 
        collection_name: str
    ) -> "Document":
        async with self.db_connector.session_ctx() as session:
            return await self.document_service.create_document_record(
                session=session,
                doc_id=doc_id,
                content_type=pdf_file.content_type,
                file_size=pdf_file.file_size,
                s3_key=s3_uploaded_key,
                collection_name=collection_name
            )


    async def _rollback_db_record(
        self,
        record: "Document",
        doc_id: str
    ) -> None:
        async with self.db_connector.session_ctx() as session:
            await self.document_service.delete_document_record(session, doc_id)


    async def delete_document(
        self,
        doc_id: str,
        collection_name: str
    ) -> Dict[str, str]:
        try:
            await self.vector_store_service.delete_document(doc_id, collection_name)
            
            async with self.db_connector.session_ctx() as session:
                success = await self.document_service.delete_document_completely(session, doc_id)
                if success:
                    logger.info(f"Document {doc_id} completely deleted from PostgreSQL and S3")
                else:
                    logger.warning(f"Document {doc_id} not found in PostgreSQL or S3 deletion failed")
            
            return {"status": "deleted", "doc_id": doc_id}
            
        except Exception as ex:
            logger.error(f"Failed to delete document {doc_id}: {ex}")
            return {"status": "error", "doc_id": doc_id, "error": str(ex)}


    async def delete_documents(
        self,
        doc_ids: list[str],
        collection_name: str
    ) -> list[dict[str, str | None]]:
        results = []
        
        for doc_id in doc_ids:
            try:
                result = await self.delete_document(doc_id, collection_name)
                results.append({
                    "doc_id": doc_id,
                    "status": result["status"],
                    "error": result.get("error")
                })
                
            except Exception as ex:
                logger.error(f"Failed to delete document {doc_id}: {ex}")
                results.append({
                    "doc_id": doc_id,
                    "status": "error",
                    "error": str(ex)
                })
        
        return results




