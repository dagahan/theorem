from typing import Any, Dict, List
import asyncio
import grpc  # type: ignore[import-untyped]
from loguru import logger
from src.grpc.grpc_utils import GrpcTools
from src.core.utils import EnvTools
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


class QdrantGrpcClient:
    def __init__(self, channel: grpc.Channel, service_name: str) -> None:
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


    async def upsert_points(
        self,
        collection_name: str,
        points: List[qm.PointStruct]
    ) -> None:
        await self._call("upsert", collection_name=collection_name, points=points, wait=True)


    async def is_document_exists(
        self,
        collection_name: str, 
        doc_id: str
    ) -> bool:
        res = await self._call(
            "count",
            collection_name=collection_name,
            count_filter=qm.Filter(must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))]),
        )
        cnt = getattr(res, "count", None)
        if cnt is None:
            cnt = (res or {}).get("count", 0)
        return bool(cnt)


    async def delete_document(
        self,
        collection_name: str,
        doc_id: str
    ) -> None:
        await self._call(
            "delete",
            collection_name=collection_name,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))])
            ),
            wait=True,
        )


    async def get_document_vectors(
        self,
        collection_name: str,
        doc_id: str
    ) -> List[List[float]]:
        res = await self._call(
            "scroll",
            collection_name=collection_name,
            scroll_filter=qm.Filter(must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))]),
            with_vectors=True,
            with_payload=False,
            limit=10000,
        )
        pts = res[0] if isinstance(res, (list, tuple)) else []

        vectors = []
        for p in pts:
            vector = getattr(p, "vector", None)
            if vector is not None:
                vectors.append(vector)
        return vectors


    async def get_document_texts(
        self,
        collection_name: str,
        doc_id: str
    ) -> List[str]:
        res = await self._call(
            "scroll",
            collection_name=collection_name,
            scroll_filter=qm.Filter(must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))]),
            with_vectors=False,
            with_payload=True,
            limit=10000,
        )
        pts = res[0] if isinstance(res, (list, tuple)) else []
        out: List[str] = []
        for p in pts:
            payload = getattr(p, "payload", None) or {}
            t = payload.get("text")
            if isinstance(t, str) and t.strip():
                out.append(t)

        return out


    async def get_document_chunks_count(
        self,
        collection_name: str,
        doc_id: str
    ) -> int:
        res = await self._call(
            "count",
            collection_name=collection_name,
            count_filter=qm.Filter(must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))]),
        )

        if hasattr(res, "count"):
            return int(res.count)
        elif isinstance(res, dict):
            return int(res.get("count", 0))
        else:
            return 0


    async def get_paragraph_chunks(
        self,
        collection_name: str,
        doc_id: str,
        paragraph_id: int
    ) -> List[Dict[str, Any]]:
        res = await self._call(
            "scroll",
            collection_name=collection_name,
            scroll_filter=qm.Filter(
                must=[
                    qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id)),
                    qm.FieldCondition(key="paragraph_id", match=qm.MatchValue(value=paragraph_id)),
                ]
            ),
            limit=1000,
        )

        results = []
    
        if isinstance(res, (list, tuple)) and len(res) > 0:
            points = res[0]
            if hasattr(points, '__iter__') and not isinstance(points, str):
                points_list = list(points)
            else:
                points_list = [points]
        else:
            points_list = []
        
        for point in points_list:
            if hasattr(point, "id") and hasattr(point, "payload"):
                payload = point.payload
                if hasattr(payload, '__dict__'):
                    payload = payload.__dict__
                results.append({"id": point.id, "payload": payload})
            elif isinstance(point, dict):
                results.append({"id": point.get("id", ""), "payload": point.get("payload", {})})
        
        return results


    async def get_window_by_chunk_id(
        self,
        collection_name: str,
        doc_id: str,
        start_id: int,
        end_id: int
    ) -> List[Dict[str, Any]]:
        res = await self._call(
            "scroll",
            collection_name=collection_name,
            scroll_filter=qm.Filter(
                must=[
                    qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id)),
                    qm.FieldCondition(key="chunk_id", range=qm.Range(gte=start_id, lte=end_id)),
                ]
            ),
            limit=1000,
        )

        results = []
        
        if isinstance(res, (list, tuple)) and len(res) > 0:
            points = res[0]
            if hasattr(points, '__iter__') and not isinstance(points, str):
                points_list = list(points)
            else:
                points_list = [points]
        else:
            points_list = []
        
        for point in points_list:
            if hasattr(point, "id") and hasattr(point, "payload"):
                payload = point.payload
                if hasattr(payload, '__dict__'):
                    payload = payload.__dict__
                results.append({"id": point.id, "payload": payload})
            elif isinstance(point, dict):
                results.append({"id": point.get("id", ""), "payload": point.get("payload", {})})
        
        return results


    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 25,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        # Get raw response before normalization to preserve ScoredPoint objects
        fn = getattr(self.qdrant_client, "search")
        raw_res = await asyncio.to_thread(
            fn,
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )
        
        logger.debug(f"Raw search response type: {type(raw_res)}, count: {len(raw_res) if hasattr(raw_res, '__len__') else 'no len'}")
        
        results: List[Dict[str, Any]] = []
        
        # Extract data directly from ScoredPoint objects
        if hasattr(raw_res, '__iter__'):
            for scored_point in raw_res:
                if hasattr(scored_point, "id") and hasattr(scored_point, "score") and hasattr(scored_point, "payload"):
                    payload = scored_point.payload
                    if hasattr(payload, '__dict__'):
                        payload = payload.__dict__
                    results.append({
                        "id": scored_point.id,
                        "score": scored_point.score,
                        "payload": payload
                    })
        
        logger.debug(f"Qdrant search: processed {len(results)} results")
        return results


    async def get_collection_documents(
        self,
        collection_name: str
    ) -> List[str]:
        res = await self._call(
            "scroll",
            collection_name=collection_name,
            scroll_filter=qm.Filter(must_not=[]),
            with_payload=True,
            with_vectors=False,
            limit=10000,
        )
        
        doc_ids = set()
        for point in (res[0] if isinstance(res, (list, tuple)) else []):
            if hasattr(point, "payload") and point.payload:
                doc_id = point.payload.get("doc_id")
                if doc_id:
                    doc_ids.add(doc_id)
            elif isinstance(point, dict) and "payload" in point:
                doc_id = point["payload"].get("doc_id")
                if doc_id:
                    doc_ids.add(doc_id)
        
        return list(doc_ids)

