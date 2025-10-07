from typing import Any, Dict, List, Any

import asyncio
import grpc  # type: ignore[import-untyped]

from loguru import logger

from src.grpc.grpc_utils import GrpcTools
from src.core.utils import EnvTools
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


class QdrantGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str, **kwargs: Any) -> None:
        self.channel = channel
        self.service_name = service_name
        self.qdrant_client = QdrantClient(
            host=EnvTools.get_service_host("qdrant"),
            grpc_port=int(EnvTools.get_service_grpc_port("qdrant")),
            prefer_grpc=True,
            timeout=30.0,
            check_compatibility=False,
            grpc_options={"grpc.enable_http_proxy": 0, "grpc.keepalive_time_ms": 60000, "grpc.keepalive_timeout_ms": 20000},
        )


    async def _call(
        self,
        method: str,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        fn = getattr(self.qdrant_client, method)
        raw = await asyncio.to_thread(fn, *args, **kwargs)
        return GrpcTools.qdrant_normalize(raw)


    async def health_check(self) -> Dict[str, Any]:
        try:
            cols = await self._call("get_collections")
            collections = cols.collections if hasattr(cols, "collections") else []
            return {"status": "healthy", "collections_count": len(collections)}

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


    async def get_collections(self) -> List[Dict[str, Any]]:
        try:
            cols = await self._call("get_collections")
            collections = cols.collections if hasattr(cols, "collections") else []
            return collections if isinstance(collections, list) else []

        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            return []


    async def get_collection(self, collection_name: str) -> Dict[str, Any]:
        try:
            collection_info = await self._call("get_collection", collection_name=collection_name)
            if isinstance(collection_info, dict):
                return collection_info
            else:
                return {
                    "config": getattr(collection_info, "config", {}),
                    "status": getattr(collection_info, "status", "unknown"),
                    "optimizer_status": getattr(collection_info, "optimizer_status", {}),
                    "payload_schema": getattr(collection_info, "payload_schema", {}),
                }

        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {e}")
            raise


    async def create_collection(
        self,
        collection_name: str,
        vector_size: int
    ) -> None:
        try:
            await self._call(
                "create_collection",
                collection_name=collection_name,
                vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
            )

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise


    async def create_collection_hybrid(
        self,
        collection_name: str,
        dense_dim: int
    ) -> None:
        try:
            await self._call(
                "create_collection",
                collection_name=collection_name,
                vectors_config={"dense": qm.VectorParams(size=dense_dim, distance=qm.Distance.COSINE)},
                sparse_vectors_config={"text": qm.SparseVectorParams()},
            )

        except Exception as e:
            logger.error(f"Failed to create hybrid collection {collection_name}: {e}")
            raise


    async def ensure_collection_hybrid(
        self,
        collection_name: str,
        dense_dim: int
    ) -> None:
        cols = await self.get_collections()
        names = [getattr(c, "name", None) or c.get("name") for c in cols]
        if collection_name not in set(filter(None, names)):
            await self.create_collection_hybrid(collection_name, dense_dim)
        else:
            await self.validate_collection_hybrid(collection_name, dense_dim)


    async def validate_collection_hybrid(
        self,
        collection_name: str,
        dense_dim: int
    ) -> None:
        try:
            collection_info = await self.get_collection(collection_name)
            config = collection_info.get("config", {})
            if not config:
                raise ValueError(f"Collection '{collection_name}' has no config")
            params = config.get("params", {})
            if not params:
                raise ValueError(f"Collection '{collection_name}' config has no params")
            vectors_config = params.get("vectors", {})
            sparse_vectors_config = params.get("sparse_vectors", {})
            if not isinstance(vectors_config, dict) or "dense" not in vectors_config:
                raise ValueError(f"Collection '{collection_name}' does not have hybrid vector configuration. Expected 'dense' vector, got: {vectors_config}")
            dense_config = vectors_config["dense"]
            if dense_config.get("size") != dense_dim:
                raise ValueError(f"Collection '{collection_name}' dense vector dimension mismatch. Expected {dense_dim}, got {dense_config.get('size')}")
            if not isinstance(sparse_vectors_config, dict) or "text" not in sparse_vectors_config:
                raise ValueError(f"Collection '{collection_name}' does not have sparse vector configuration. Expected 'text' sparse vector, got: {sparse_vectors_config}")
            logger.info(f"Collection '{collection_name}' is compatible with hybrid vector configuration")
        except Exception as e:
            logger.error(f"Collection validation failed: {e}")
            raise ValueError(f"Collection '{collection_name}' is not compatible with hybrid vector configuration: {e}")
















    async def search_dense(
        self,
        collection_name: str,
        vector: List[float],
        limit: int
    ) -> List[Dict[str, Any]]:
        res = await asyncio.to_thread(
            self.qdrant_client.search,
            collection_name=collection_name,
            query_vector=qm.NamedVector(name="dense", vector=vector),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        out: List[Dict[str, Any]] = []
        for sp in res or []:
            out.append({"id": sp.id, "score": sp.score, "payload": getattr(sp, "payload", {})})
        return out


    async def search_sparse(
        self,
        collection_name: str,
        indices: List[int],
        values: List[float],
        limit: int
    ) -> List[Dict[str, Any]]:
        res = await asyncio.to_thread(
            self.qdrant_client.search,
            collection_name=collection_name,
            query_vector=qm.NamedSparseVector(
                name="text",
                vector=qm.SparseVector(indices=indices, values=values),
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        out: List[Dict[str, Any]] = []
        for sp in res or []:
            out.append({"id": sp.id, "score": sp.score, "payload": getattr(sp, "payload", {})})
        return out



