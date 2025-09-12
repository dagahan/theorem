from fastapi import APIRouter, HTTPException
from loguru import logger

from pydantic_schemas import ServiceStats

from src.services.statistics_service import StatisticsService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


def get_statistics_router(database_connector: "DataBaseConnector") -> APIRouter:
    router = APIRouter(prefix="/statistics", tags=["statistics"])
    statistics_service = StatisticsService(database_connector)


    @router.get("/service_stats", response_model=ServiceStats)  # type: ignore[misc]
    async def get_service_stats() -> ServiceStats:
        try:
            stats = await statistics_service.get_service_stats()
            return stats
            
        except Exception as e:
            logger.error(f"Get service stats failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


    return router


