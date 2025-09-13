from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from loguru import logger

from pydantic_schemas import SearchWithContextRequest, SearchResponse

from src.services.searching_engine_service import SearchingEngineService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


def get_search_router(database_connector: "DataBaseConnector") -> APIRouter:
    router = APIRouter(prefix="/search", tags=["search"])
    searching_engine_service = SearchingEngineService(database_connector)


    @router.post("/search_with_context", response_model=SearchResponse)  # type: ignore[misc]
    async def search_with_context(
        request: SearchWithContextRequest
    ) -> SearchResponse:
        try:
            logger.debug(f"Search request: query='{request.query}', collection='{request.collection_name}'")

            result = await searching_engine_service.search_with_context(
                query=request.query,
                collection_name=request.collection_name,
                top_k=request.top_k,
                neighbor_window=request.neighbor_window,
                include_whole_paragraph=request.include_whole_paragraph
            )

            return SearchResponse(merged_text=result["merged_text"])
            
        except Exception as e:
            logger.error(f"Search with context failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    return router



