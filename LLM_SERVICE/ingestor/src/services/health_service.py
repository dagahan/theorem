from __future__ import annotations

import asyncio
from typing import Any, Dict, Tuple, Union
from loguru import logger

from src.grpc.client.hybrid_embedder_grpc_client import HybridEmbedderGrpcClient
from src.grpc.client.qdrant_grpc_client import QdrantGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.db.database_connector import DataBaseConnector


class HealthService:
    def __init__(self, database_connector: "DataBaseConnector") -> None:
        self.db_connector = database_connector
        self.hybrid_embedder_grpc_client = GrpcClientRegistry().register_client("hybrid_embedder", HybridEmbedderGrpcClient)
        self.qdrant_grpc_client = GrpcClientRegistry().register_client("qdrant", QdrantGrpcClient)


    async def health_check_service(
        self,
        service_name: str
    ) -> Union[str, Tuple[Dict[str, Any], str, Dict[str, Any], str]]:
        async def _check_hybrid_embedder() -> Dict[str, Any]:
            try:
                return await self.hybrid_embedder_grpc_client.health_check()
            except Exception as ex:
                return {"status": "unhealthy", "model_id": "", "dim": 0}

        async def _check_qdrant() -> str:
            try:
                h = await self.qdrant_grpc_client.health_check()
                return str(h.get("status", "unknown"))
            except Exception as e:
                return "unhealthy"

        async def _check_postgres() -> Dict[str, Any]:
            try:
                return await self.db_connector.health_check()
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

        async def _check_s3() -> str:
            try:
                from src.s3.s3_connector import S3Client
                s3_client = S3Client()
                return "healthy"
            except Exception as e:
                return "unhealthy"

        name = service_name.lower()
        if name == "hybrid_embedder":
            return str((await _check_hybrid_embedder()).get("status", "unknown"))
        if name == "qdrant":
            return await _check_qdrant()
        if name == "postgres":
            pg_health = await _check_postgres()
            return str(pg_health.get("status", "unknown"))
        if name == "s3":
            return await _check_s3()
        if name == "all":
            emb, q, pg, s3 = await asyncio.gather(
                _check_hybrid_embedder(), 
                _check_qdrant(), 
                _check_postgres(), 
                _check_s3()
            )

            return emb, q, pg, s3

        raise ValueError(f"Unknown service name: {service_name}")


    async def ensure_all_healthy(self) -> Dict[str, Any]:
        health = await self.health_check_service("all")
        assert isinstance(health, tuple)
        hybrid_embedder_health, qdrant_status, postgres_health, s3_status = health

        if (hybrid_embedder_health.get("status") != "healthy" or 
            qdrant_status != "healthy" or 
            postgres_health.get("status") != "healthy" or 
            s3_status != "healthy"):
                raise RuntimeError(
                    f"Services unavailable. Hybrid embedder: {hybrid_embedder_health.get('status')}, "
                    f"Qdrant: {qdrant_status}, PostgreSQL: {postgres_health.get('status')}, "
                    f"S3: {s3_status}"
                )

        return hybrid_embedder_health
