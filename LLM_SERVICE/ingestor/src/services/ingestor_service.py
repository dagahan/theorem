from __future__ import annotations
import os
import re
import unicodedata
from typing import List, Dict, Any, Optional, Union, Tuple
from loguru import logger
import asyncio

from src.services.chunking_service import ChunkingService
from src.services.document_service import DocumentService
from src.services.text_normalize_service import TextNormalizeService
from src.services.health_service import HealthService
from src.services.vector_store_service import VectorStoreService
from src.services.searching_engine_service import SearchingEngineService
from src.services.statistics_service import StatisticsService
from src.services.id_service import IdService
from src.grpc.client.embedder_grpc_client import EmbedderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.core.utils import EnvTools

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
        self.searching_engine_service = SearchingEngineService(database_connector)
        self.statistics_service = StatisticsService(database_connector)
        self.db_connector = database_connector
        self.embedder_grpc_client = GrpcClientRegistry().register_client("embedder", EmbedderGrpcClient)


    async def ingest_file(
        self,
        file_text: str,
        file_metadata: Dict[str, Any],
        collection_name: Optional[str] = None,
        file_content: Optional[bytes] = None,
    ) -> None:
        collection = collection_name or self.vector_store_service.collection_name
        doc_id = IdService.from_filename(file_metadata)

        await self.vector_store_service.ensure_collection_exists(collection)
        if await self.vector_store_service.is_document_exists(collection, doc_id):
            raise ValueError(f"Document with id '{doc_id}' already exists in collection '{collection}'. "
                             f"File name (without extension) must be unique.")

        await self.health_service.ensure_all_healthy()

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

        normalized_text = self.text_normalize_service.normalize_text(
            file_text,
            doc_id,
            file_metadata
        )
        
        chunks = self.chunking_service.chunk_text(
            doc_id,
            normalized_text,
            file_metadata
        )

        if not chunks:
            logger.warning(f"No chunks produced for {doc_id}")
            if s3_key:
                await self.document_service.delete_file_from_s3(s3_key)
            return

        embeds = await self.embedder_grpc_client.embed_batch(
            [str(c["text"]) for c in chunks],
            normalize=True
        )

        if len(embeds) != len(chunks):
            if s3_key:
                await self.document_service.delete_file_from_s3(s3_key)
            raise RuntimeError("Embedding count mismatch")

        points = self.vector_store_service.build_points(
            chunks,
            embeds
        )
        
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
        collection_name: Optional[str] = None
    ) -> Dict[str, str]:
        if await self.health_service.health_check_service("qdrant") != "healthy":
            return {"status": "unsuccessful", "doc_id": doc_id}

        if collection_name is None:
            collection_name = self.vector_store_service.collection_name
        
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




