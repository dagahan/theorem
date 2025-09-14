from __future__ import annotations

from typing import Dict, Any, List

from loguru import logger
from sqlalchemy import select, delete

from pydantic_schemas import Document
from src.s3.s3_connector import S3Client
from src.services.id_service import IdService
import mimetypes

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.data_classes.data_classes import PdfFile


class DocumentService:
    def __init__(self) -> None:
        self.s3_client = S3Client()
        self.id_service = IdService()


    async def create_document_record(
        self,
        session: "AsyncSession",
        doc_id: str,
        content_type: str,
        file_size: int,
        s3_key: str,
        collection_name: str
    ) -> Document:
        await self._ensure_table_exists(session)
        
        document = Document(
            doc_id=doc_id,
            content_type=content_type,
            file_size=file_size,
            s3_bucket=self.s3_client.bucket_name,
            s3_key=s3_key,
            collection_name=collection_name
        )
        
        session.add(document)
        await session.commit()
        await session.refresh(document)
        
        logger.info(f"Document record created: {doc_id} -> {s3_key}")
        return document


    async def upload_file_to_s3(
        self,
        doc_id: str,
        collection_name: str,
        file_content: bytes,
        content_type: str
    ) -> str:
        s3_key = self.id_service.make_s3_key(collection_name, doc_id)
        
        try:
            await self.s3_client.upload_bytes(
                data=file_content,
                s3_key=s3_key,
                content_type=content_type,
            )

            logger.info(f"File uploaded to S3: {doc_id} -> {s3_key}")
            return s3_key

        except Exception as ex:
            logger.error(f"Failed to upload file to S3: {doc_id}, error: {ex}")
            raise RuntimeError(f"S3 upload failed for {doc_id}: {str(ex)}") from ex


    async def required_upload_file_to_s3(
        self,
        pdf: "PdfFile",
        collection_name: str
    ) -> str:
        return await self.upload_file_to_s3(
            pdf.doc_id,
            collection_name,
            pdf.content,
            pdf.content_type
        )


    async def get_document_by_doc_id(
        self,
        session: "AsyncSession",
        doc_id: str
    ) -> Document | None:
        result = await session.execute(
            select(Document).where(Document.doc_id == doc_id)
        )
        return result.scalar_one_or_none()


    async def get_documents_by_collection(
        self,
        session: "AsyncSession",
        collection_name: str
    ) -> List[Document]:
        result = await session.execute(
            select(Document).where(Document.collection_name == collection_name)
        )
        return list(result.scalars().all())


    async def delete_document_record(
        self,
        session: "AsyncSession",
        doc_id: str
    ) -> Document | None:
        document = await self.get_document_by_doc_id(session, doc_id)
        if not document:
            logger.warning(f"Document not found in database: {doc_id}")
            return None

        await session.execute(
            delete(Document).where(Document.doc_id == doc_id)
        )
        await session.commit()
        
        logger.info(f"Document record deleted from database: {doc_id}")
        return document


    async def delete_file_from_s3(
        self,
        s3_key: str
    ) -> bool:
        try:
            await self.s3_client.delete_object(s3_key)
            logger.info(f"File deleted from S3: {s3_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file from S3: {s3_key}, error: {e}")
            return False


    async def delete_document_completely(
        self,
        session: "AsyncSession",
        doc_id: str
    ) -> bool:
        document = await self.delete_document_record(session, doc_id)
        if not document:
            return False

        s3_deleted = await self.delete_file_from_s3(document.s3_key)
        if not s3_deleted:
            logger.warning(f"S3 deletion failed for document: {doc_id}, but database record was deleted")

        return True


    async def _ensure_table_exists(self, session: "AsyncSession") -> None:
        try:
            # Try to query the table to check if it exists
            await session.execute(select(Document).limit(1))
            
        except Exception as e:
            if "relation" in str(e).lower() and "does not exist" in str(e).lower():
                logger.warning("Documents table does not exist, creating it...")
                from pydantic_schemas import Base
                await session.run_sync(Base.metadata.create_all)
                await session.commit()
                logger.info("Documents table created successfully")
            else:
                raise


    async def get_document_info(
        self,
        session: "AsyncSession",
        doc_id: str
    ) -> Dict[str, Any] | None:
        document = await self.get_document_by_doc_id(session, doc_id)
        if not document:
            return None

        return {
            "doc_id": document.doc_id,
            "filename": f"{doc_id}{mimetypes.guess_extension(document.content_type) or ".bin"}",
            "content_type": document.content_type,
            "file_size": document.file_size,
            "collection_name": document.collection_name,
            "s3_url": self.s3_client.public_url(document.s3_key),
            "created_at": document.created_at,
            "updated_at": document.updated_at
        }


