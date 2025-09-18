from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from loguru import logger

from pydantic_schemas import (
    CollectionInfo,
    ListCollectionsResponse,
    GetDocumentResponse,
)

from src.services.vector_store_service import VectorStoreService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


def get_vector_store_router(database_connector: "DataBaseConnector") -> APIRouter:
    router = APIRouter(prefix="/vector-store", tags=["vector-store"])
    vector_store_service = VectorStoreService()


    @router.get("/get_document_info/{doc_id}", response_model=GetDocumentResponse)  # type: ignore[misc]
    async def get_document_info(
        doc_id: str,
        collection_name: str
    ) -> GetDocumentResponse:
        try:
            chunks_count = await vector_store_service.get_document_chunks_count(doc_id, collection_name)
            return GetDocumentResponse(
                doc_id=doc_id,
                chunks_count=chunks_count,
                status="success"
            )

        except Exception as e:
            logger.error(f"Failed to get document info: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.get("/get_document_embedded/{doc_id}", response_model=Dict[str, Any])  # type: ignore[misc]
    async def get_document_embedded(
        doc_id: str,
        collection_name: str
    ) -> Dict[str, Any]:
        try:
            vectors = await vector_store_service.get_document_vectors(doc_id, collection_name)
            return {
                "doc_id": doc_id,
                "vectors": vectors,
                "vector_count": len(vectors),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Get document embedded failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.get("/get_document_text/{doc_id}", response_model=Dict[str, Any])  # type: ignore[misc]
    async def get_document_text(
        doc_id: str,
        collection_name: str
    ) -> Dict[str, Any]:
        try:
            texts = await vector_store_service.get_document_texts(doc_id, collection_name)
            return {
                "doc_id": doc_id,
                "texts": texts,
                "text_count": len(texts),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Get document text failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    @router.get("/list_collections", response_model=ListCollectionsResponse)  # type: ignore[misc]
    async def list_collections() -> ListCollectionsResponse:
        try:
            collections_data = await vector_store_service.get_collections()
            collection_infos = [
                CollectionInfo(
                    name=col["name"],
                    status=col["status"],
                    documents=col["documents"]
                )
                for col in collections_data
            ]
            return ListCollectionsResponse(
                collections=collection_infos,
                total_collections=len(collection_infos),
                status="success"
            )
            
        except Exception as e:
            logger.error(f"List collections failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    return router


