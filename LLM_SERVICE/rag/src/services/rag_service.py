import asyncio

import grpc  # type: ignore
from loguru import logger

from typing import Any

from protobuf_stubs import rag_pb2, rag_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.services.searching_engine_service import SearchingEngineService
from src.services.health_service import HealthService

import threading

import re

grpc_tools = GrpcTools()


class RAGService(rag_pb2_grpc.RAGServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, name="rag-async-loop", daemon=True)
        self.async_thread.start()

        self.searching_engine = SearchingEngineService()
        self.health_checker = HealthService()
        self._run_async_task(self._initialize_services())


    def _run_async_loop(self) -> None:
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()


    def _run_async_task(self, coro: Any) -> Any:
        future = asyncio.run_coroutine_threadsafe(coro, self.async_loop)
        return future.result()


    async def _initialize_services(self) -> None:
        self.searching_engine = SearchingEngineService()
        self.health_checker = HealthService()


    @grpc_tools.log_grpc_request("Health")
    def Health(
        self,
        request: rag_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> rag_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            embedder_status, qdrant_status, embedder_model_id, embedder_dim = self._run_async_task(
                self.health_checker.health_check_service("all")
            )

            overall_status = "healthy" if embedder_status == "healthy" and qdrant_status == "healthy" else "unhealthy"

            response = rag_pb2.HealthResponse(
                status=overall_status,
                embedder_status=embedder_status,
                qdrant_status=qdrant_status,
                embedder_model_id=embedder_model_id,
                embedder_dim=embedder_dim,
            )
            grpc_tools.validate_proto(response, context)
            return response

        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return rag_pb2.HealthResponse(
                status="unhealthy",
                embedder_status="unknown",
                qdrant_status="unknown",
                embedder_model_id="",
                embedder_dim=0
            )


    @grpc_tools.log_grpc_request("Search")
    def Search(
        self,
        request: rag_pb2.SearchRequest,
        context: grpc.ServicerContext,
    ) -> rag_pb2.SearchResponse:
        try:
            grpc_tools.validate_proto(request, context)

            search_result = self._run_async_task(
                self.searching_engine.retrieve_context(
                    query=request.query,
                    collection_name=request.collection_name
                )
            )

            context_windows = search_result.get("context_windows", [])

            if not context_windows:
                response = rag_pb2.SearchResponse(results=[], success=False, error="context_not_found")
                grpc_tools.validate_proto(response, context)
                return response

            search_results = []
            for window in context_windows:
                search_results.append(
                    rag_pb2.SearchResult(
                        doc_id=window.get("doc_id", ""),
                        text=window.get("context_text", ""),
                        score=window.get("relevance_score", 0.0),
                        pages=window.get("pages", []),
                        paragraph_id=window.get("paragraph_id", 0),
                        chunk_id=window.get("chunk_id", 0),
                    )
                )

            response = rag_pb2.SearchResponse(
                results=search_results,
                success=True,
                error="",
            )

            grpc_tools.validate_proto(response, context)
            return response

        except Exception as ex:
            logger.exception("Search failed")
            return rag_pb2.SearchResponse(results=[], success=False, error=str(ex))


