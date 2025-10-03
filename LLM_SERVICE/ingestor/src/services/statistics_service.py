from __future__ import annotations

from loguru import logger

from src.services.health_service import HealthService
from src.services.vector_store_service import VectorStoreService
from pydantic_schemas import ServiceStats

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


class StatisticsService:
    def __init__(self, database_connector: "DataBaseConnector") -> None:
        self.health_service = HealthService(database_connector)
        self.vector_store_service = VectorStoreService()


    async def get_service_stats(self) -> ServiceStats:
        total_collections = 0
        total_vectors = 0
        error_messages = []
        
        try:
            health_result = await self.health_service.health_check_service("all")
            if isinstance(health_result, tuple) and len(health_result) == 4:
                hybrid_embedder_health, qdrant_status, postgres_health, s3_status = health_result
                hybrid_embedder_status = hybrid_embedder_health.get("status", "unknown")
                hybrid_embedder_model_id = hybrid_embedder_health.get("model_id", "")
                hybrid_embedder_dim = hybrid_embedder_health.get("dim", 0)
            else:
                raise ValueError("Unexpected health check result format")
                    
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            hybrid_embedder_status = "unknown"
            hybrid_embedder_model_id = ""
            hybrid_embedder_dim = 0
            qdrant_status = "unknown"
            error_messages.append(f"Health check failed: {str(ex)}")
        
        if qdrant_status == "healthy":
            try:
                total_collections, total_vectors = await self.vector_store_service.get_collections_stats()
                
            except Exception as e:
                error_messages.append(f"Failed to get collections: {str(e)}")
                logger.warning(f"Failed to get collections: {e}")
        else:
            error_messages.append("Skipping collection stats due to unhealthy vector store")
        
        return ServiceStats(
            total_collections=total_collections,
            total_vectors=total_vectors,
            hybrid_embedder_status=hybrid_embedder_status,
            hybrid_embedder_model_id=hybrid_embedder_model_id,
            hybrid_embedder_dim=hybrid_embedder_dim,
            qdrant_status=qdrant_status,
            error_message="; ".join(error_messages) if error_messages else ""
        )



        
