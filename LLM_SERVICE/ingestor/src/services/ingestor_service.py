from __future__ import annotations
from typing import List, Dict, Any
from loguru import logger

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

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


class IngestorService:
    def __init__(self, database_connector: "DataBaseConnector") -> None:
        self.chunking_service = ChunkingService()
        self.document_service = DocumentService()
        self.text_normalize_service = TextNormalizeService()
        self.health_service = HealthService(database_connector)
        self.vector_store_service = VectorStoreService()
        self.statistics_service = StatisticsService(database_connector)
        self.db_connector = database_connector
        self.embedder_grpc_client = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)


    async def ingest_file(
        self,
        file_metadata: Dict[str, Any],
        collection_name: str,
        file_content: bytes | None = None,
    ) -> None:
        collection = collection_name
        doc_id = IdService.from_filename(file_metadata)

        await self.vector_store_service.ensure_collection_exists(collection)
        if await self.vector_store_service.is_document_exists(collection, doc_id):
            raise ValueError(f"Document with id '{doc_id}' already exists in collection '{collection}'. "
                             f"File name (without extension) must be unique.")

        s3_key = None
        if file_content:
            filename = file_metadata.get("filename", "unknown")
            content_type = file_metadata.get("content_type", "application/octet-stream")
            
            s3_key = await self.document_service.upload_file_to_s3(
                file_content=file_content,
                filename=filename,
                content_type=content_type,
                collection_name=collection,
                doc_id=doc_id
            )

        if file_content is None:
            raise ValueError("File content is required for PDF processing")
        
        file_parser_service = FileParserService()
        
        blocks = file_parser_service.extract_blocks_from_pdf(
            filename=file_metadata.get("filename", ""),
            content=file_content,
            content_type=file_metadata.get("content_type"),
            doc_id=doc_id,
            metadata=file_metadata
        )

        chunks = self.chunking_service.chunk_blocks(
            doc_id,
            blocks,
            file_metadata
        )

        if not chunks:
            logger.warning(f"No chunks produced for {doc_id}")
            if s3_key:
                await self.document_service.delete_file_from_s3(s3_key)
            return

        converted_chunks = []
        paragraph_id = 0
        chunk_id = 0
        
        for chunk in chunks:
            chunk_id += 1
            converted_chunks.append({
                "doc_id": doc_id,
                "paragraph_id": paragraph_id,
                "chunk_id": chunk_id,
                "text": chunk["text"]
            })

        embeds = await self.embedder_grpc_client.embed_batch(
            [str(c["text"]) for c in converted_chunks],
            normalize=True
        )

        if len(embeds) != len(converted_chunks):
            if s3_key:
                await self.document_service.delete_file_from_s3(s3_key)
            raise RuntimeError("Embedding count mismatch")
            
        successful_embeds = [e for e in embeds if e.get("success", False)]
        if not successful_embeds:
            if s3_key:
                await self.document_service.delete_file_from_s3(s3_key)
            raise RuntimeError("No successful embeddings generated")

        points = self.vector_store_service.build_points(
            converted_chunks,
            embeds
        )
        
        logger.debug(f"Built {len(points)} points for upsert")
        
        try:
            await self.vector_store_service.upsert_batched_to_collection(
                collection,
                points
            )
            
            if file_content and s3_key:
                async with self.db_connector.session_ctx() as session:
                    await self.document_service.create_document_record(
                        session=session,
                        doc_id=doc_id,
                        content_type=content_type,
                        file_size=len(file_content),
                        s3_key=s3_key,
                        collection_name=collection
                    )
            
            logger.info(f"Document {doc_id} successfully ingested with {len(chunks)} chunks" + 
                       (f" and stored in S3: {s3_key}" if s3_key else ""))
                       
        except Exception as ex:
            if s3_key:
                logger.warning(f"Cleaning up S3 file {s3_key} due to Qdrant upsert failure")
                await self.document_service.delete_file_from_s3(s3_key)
            raise RuntimeError(f"Failed to ingest document {doc_id}: {str(ex)}") from ex


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




