import asyncio
import time
from datetime import datetime

import grpc  # type: ignore
from loguru import logger

from typing import Any, Dict, List

from protobuf_stubs import rag_pb2, rag_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.core.logging import ResponseLogger
from src.services.searching_engine_service import SearchingEngineService
from src.services.health_service import HealthService

import threading

grpc_tools = GrpcTools()


class RAGService(rag_pb2_grpc.RAGServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop_forever, args=(self._loop,), name="rag-async-loop", daemon=True).start()
        self._run = lambda coro: asyncio.run_coroutine_threadsafe(coro, self._loop).result()

        self.searching_engine = SearchingEngineService()
        self.health_checker = HealthService()


    @staticmethod
    def _loop_forever(loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()


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

            result: Dict[str, Any] = self._run(  # type: ignore
                self.searching_engine.retrieve_context(
                    query=request.query, collection_name=request.collection_name
                )
            )

            windows: List[Dict[str, Any]] = result.get("context_windows", [])
            if not windows:
                return rag_pb2.SearchResponse(result="", success=False, error="context_not_found")

            # Format response as continuous text with scores
            formatting_start = time.time()
            formatted_text = self._format_response_as_text(windows)
            formatting_time_ms = (time.time() - formatting_start) * 1000
            
            ResponseLogger.log_response_formatting(windows, formatted_text, formatting_time_ms)

            response = rag_pb2.SearchResponse(
                result=formatted_text,
                success=True,
                error=""
            )

            return response

        except Exception as ex:
            logger.exception("Search failed")
            return rag_pb2.SearchResponse(result="", success=False, error=str(ex))

    def _format_response_as_text(self, windows: List[Dict[str, Any]]) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        digest_lines = []
        evidence_lines = []
        
        for i, window in enumerate(windows[:10], 1):
            score = window.get("relevance_score", 0.0)
            text = window.get("context_text", "")
            doc_id = window.get("doc_id", "unknown")
            pages = window.get("pages", [])
            paragraph_id = window.get("paragraph_id", 0)
            chunk_id = window.get("chunk_id", 0)
            
            context_id = f"{doc_id}#p{paragraph_id}#c{chunk_id}"
            pages_str = f"{min(pages)}-{max(pages)}" if pages and len(pages) > 1 else str(pages[0]) if pages else "unknown"
            
            digest_line = f"- {text[:100]}{'...' if len(text) > 100 else ''} [{context_id}]"
            digest_lines.append(digest_line)
            
            evidence_line = f"- id:{context_id} | score:{score:.4f} | pages:{pages_str} | type:quote\n  \"{text[:400]}{'...' if len(text) > 400 else ''}\""
            evidence_lines.append(evidence_line)
        
        digest_section = "\n".join(digest_lines[:5])
        evidence_section = "\n".join(evidence_lines[:5])
        
        formatted_context = f"""# digest
{digest_section}

# evidence
{evidence_section}"""
        
        return formatted_context


