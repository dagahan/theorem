from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, TYPE_CHECKING, Callable, Coroutine
from loguru import logger

if TYPE_CHECKING:
    import grpc  # type: ignore

from protobuf_stubs import retriever_pb2, retriever_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.services.retrieve_orchestrator import RetrieveOrchestrator
from src.services.health_service import HealthService


grpc_tools = GrpcTools()


class RetrieverService(retriever_pb2_grpc.RetrieverServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop_forever, args=(self._loop,), name="retriever-async-loop", daemon=True).start()
        self._run: Callable[[Coroutine[Any, Any, Any]], Any] = lambda coro: asyncio.run_coroutine_threadsafe(coro, self._loop).result()
        self.retrieve_orchestrator = RetrieveOrchestrator()
        self.health_checker = HealthService()


    @staticmethod
    def _loop_forever(loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()


    @grpc_tools.log_grpc_request("Health")
    def Health(self, request: retriever_pb2.HealthRequest, context: grpc.ServicerContext) -> retriever_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)
            embedder_status, qdrant_status, embedder_model_id, embedder_dim = self._run(
                self.health_checker.health_check_service("all")
            )
            overall = "healthy" if embedder_status == "healthy" and qdrant_status == "healthy" else "unhealthy"
            resp = retriever_pb2.HealthResponse(
                status=overall,
                embedder_status=embedder_status,
                qdrant_status=qdrant_status,
                embedder_model_id=embedder_model_id,
                embedder_dim=embedder_dim,
            )
            grpc_tools.validate_proto(resp, context)
            return resp
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return retriever_pb2.HealthResponse(
                status="unhealthy",
                embedder_status="unknown",
                qdrant_status="unknown",
                embedder_model_id="",
                embedder_dim=0
            )


    @grpc_tools.log_grpc_request("Retrieve")
    def Retrieve(self, request: retriever_pb2.RetrieveRequest, context: grpc.ServicerContext) -> retriever_pb2.RetrieveResponse:
        try:
            grpc_tools.validate_proto(request, context)
            search_result = self._run(
                self.retrieve_orchestrator.retrieve(
                    query=request.query,
                    collection_name=request.collection_name
                )
            )

            results = []

            for chunk in search_result.chunks:
                results.append(retriever_pb2.RetrieveResult(
                    doc_id=chunk["doc_id"],
                    paragraph_id=chunk["paragraph_id"],
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    pages=chunk["pages"],
                    score=chunk["score"]
                ))
            
            return retriever_pb2.RetrieveResponse(
                results=results,
                success=True,
                error=""
            )

        except Exception as ex:
            logger.exception("Search failed")
            return retriever_pb2.RetrieveResponse(results=[], success=False, error=str(ex))


