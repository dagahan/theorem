from __future__ import annotations

import asyncio
from typing import Any, Dict, Tuple, Union
from loguru import logger

from src.grpc.client.hybrid_embedder_grpc_client import HybridEmbedderGrpcClient
from src.grpc.client.qdrant_grpc_client import QdrantGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry


class HealthService:
    def __init__(self) -> None:
        self.grpc_registry = GrpcClientRegistry()


    async def health_check_service(
        self,
        service_name: str
    ) -> Union[str, Tuple[str, str, str, int]]:
        async def _check_hybrid_embedder() -> Dict[str, Any]:
            try:
                hybrid_client = self.grpc_registry.register_client("hybrid_embedder", HybridEmbedderGrpcClient)
                result = await hybrid_client.health_check()
                return result
            except Exception as ex:
                logger.warning(f"Hybrid embedder health check failed: {ex}")
                return {"status": "unhealthy", "model_id": "", "dim": 0}

        async def _check_qdrant() -> str:
            try:
                qdrant_client = self.grpc_registry.register_client("qdrant", QdrantGrpcClient)
                h = await qdrant_client.health_check()
                return str(h.get("status", "unknown"))
            except Exception as ex:
                logger.warning(f"Qdrant health check failed: {ex}")
                return "unhealthy"

        name = service_name.lower()
        if name == "hybrid_embedder":
            return str((await _check_hybrid_embedder()).get("status", "unknown"))
        if name == "qdrant":
            return await _check_qdrant()
        if name == "all":
            emb, q = await asyncio.gather(
                _check_hybrid_embedder(), 
                _check_qdrant(),
            )

            hybrid_embedder_status = emb.get("status", "unknown") if isinstance(emb, dict) else "unknown"
            qdrant_status = q if isinstance(q, str) else "unknown"
            hybrid_embedder_model_id = emb.get("model_id")
            hybrid_embedder_dim = emb.get("dim")

            return hybrid_embedder_status, qdrant_status, hybrid_embedder_model_id, hybrid_embedder_dim

        raise ValueError(f"Unknown service name: {service_name}")


    async def ensure_all_healthy(self) -> None:
        hybrid_embedder_status, qdrant_status, _, _ = await self.health_check_service("all")  # type: ignore

        if hybrid_embedder_status != "healthy" or qdrant_status != "healthy":
            raise RuntimeError(
                f"Services unavailable. Hybrid embedder: {hybrid_embedder_status}, "
                f"Qdrant: {qdrant_status}"
            )
