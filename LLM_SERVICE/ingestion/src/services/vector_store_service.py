import uuid
import time
from typing import List, Dict, Any, Optional, Tuple

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.core.utils import EnvTools


_RETRIES = 3
_SLEEP = 0.5


class VectorStoreService:
    def __init__(self) -> None:
        host = EnvTools.required_load_env_var("QDRANT_HOST")
        port = int(EnvTools.required_load_env_var("QDRANT_PORT"))
        self.client = QdrantClient(host=host, port=port, timeout=30.0)


    def ensure_collection(
        self,
        collection_name: str,
        vector_size: int
    ) -> None:
        try:
            self.client.get_collection(collection_name)
            return

        except Exception:
            pass
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )


    async def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ) -> None:

        qpoints = []
        for p in points:
            qpoints.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector=p["vector"],
                payload=p["payload"],
            ))

        for i in range(0, len(qpoints), 256):
            batch = qpoints[i:i+256]
            for attempt in range(_RETRIES):
                try:
                    self.client.upsert(collection_name=collection_name, points=batch, wait=True)
                    break
                except Exception as e:
                    if attempt == _RETRIES - 1:
                        raise
                    logger.warning(f"upsert retry {attempt+1}: {e}")
                    time.sleep(_SLEEP)


    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 25,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:

        res = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )

        return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in res]


    async def delete_document(
        self,
        collection_name: str,
        doc_id: str
    ) -> None:
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[models.FieldCondition(
                    key="doc_id",
                    match=models.MatchValue(value=doc_id),
                )])
            ),
            wait=True,
        )


    async def get_collections(self) -> List[Dict[str, Any]]:
        cols = self.client.get_collections().collections
        out: List[Dict[str, Any]] = []
        for c in cols:
            cfg = c.config
            try:
                v = cfg.params.vectors
                if isinstance(v, models.VectorParams):
                    size = v.size
                    dist = v.distance.name
                else:
                    size = next(iter(v.values())).size
                    dist = next(iter(v.values())).distance.name

            except Exception:
                size, dist = 0, "UNKNOWN"
            out.append({"name": c.name, "vectors_count": c.points_count, "config": {
                "vector_size": size, "distance": dist
            }})

        return out


    async def get_collection_info(
        self,
        collection_name: str
    ) -> Dict[str, Any]:

        info = self.client.get_collection(collection_name)
        v = info.config.params.vectors
        if isinstance(v, models.VectorParams):
            size = v.size
            dist = v.distance.name

        else:
            size = next(iter(v.values())).size
            dist = next(iter(v.values())).distance.name

        return {"name": collection_name, "vectors_count": info.points_count,
                "config": {"vector_size": size, "distance": dist}}


    async def get_document_chunks_count(
        self,
        collection_name: str,
        doc_id: str
    ) -> int:
        total = 0
        next_off: Optional[int] = None

        while True:
            points, next_off = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=[models.FieldCondition(
                    key="doc_id", match=models.MatchValue(value=doc_id)
                )]),
                with_payload=False,
                limit=10_000,
                offset=next_off,
            )

            total += len(points)
            if not next_off:
                break

        return total


    async def get_paragraph_chunks(
        self,
        collection_name: str,
        doc_id: str,
        paragraph_id: int,
        limit: int = 10_000
    ) -> List[Dict[str, Any]]:

        res, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id)),
                models.FieldCondition(key="paragraph_id", match=models.MatchValue(value=paragraph_id)),
            ]),
            with_payload=True,
            limit=limit,
        )

        items = []

        for p in res:
            items.append({"id": p.id, "payload": p.payload})

        items.sort(key=lambda x: x["payload"].get("chunk_id", 0))

        return items


    async def get_window_by_chunk_id(
        self,
        collection_name: str,
        doc_id: str,
        start_id: int,
        end_id: int,
        limit: int = 10_000
    ) -> List[Dict[str, Any]]:

        res, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id)),
                models.FieldCondition(
                    key="chunk_id",
                    range=models.Range(gte=start_id, lte=end_id),
                ),
            ]),
            with_payload=True,
            limit=limit,
        )

        items = [{"id": p.id, "payload": p.payload} for p in res]
        items.sort(key=lambda x: x["payload"].get("chunk_id", 0))

        return items


    async def health_check(self) -> Dict[str, str]:
        try:
            self.client.get_collections()
            return {"status": "healthy"}
            
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}


