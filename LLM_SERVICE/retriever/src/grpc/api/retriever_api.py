from __future__ import annotations

from typing import TYPE_CHECKING
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
        self.retrieve_orchestrator = RetrieveOrchestrator()
        self.health_checker = HealthService()


    @grpc_tools.log_grpc_request("Health")
    async def Health(
        self,
        request: retriever_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> retriever_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_result = await self.health_checker.health_check_service("all")
            embedder_status, qdrant_status, embedder_model_id, embedder_dim = health_result  # type: ignore

            overall = "healthy" if embedder_status == "healthy" and qdrant_status == "healthy" else "unhealthy"

            details = []
            if embedder_status != 'healthy':
                details.append(f'embedder:{embedder_status}')
            if qdrant_status != 'healthy':
                details.append(f'qdrant:{qdrant_status}')

            response = retriever_pb2.HealthResponse(
                status=overall,
                success=overall == 'healthy',
                details=', '.join(details),
                embedder_status=embedder_status,
                qdrant_status=qdrant_status,
                embedder_model_id=embedder_model_id,
                embedder_dim=embedder_dim,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Health check failed: {ex}")
            return retriever_pb2.HealthResponse(
                status='unhealthy',
                success=False,
                details=str(ex),
                embedder_status='unknown',
                qdrant_status='unknown',
                embedder_model_id='',
                embedder_dim=0,
            )


    @grpc_tools.log_grpc_request("Retrieve")
    async def Retrieve(
        self,
        request: retriever_pb2.RetrieveRequest,
        context: grpc.ServicerContext,
    ) -> retriever_pb2.RetrieveResponse:
        try:
            grpc_tools.validate_proto(request, context)

            search_result = await self.retrieve_orchestrator.retrieve(
                question=request.question,
                collection_name=request.collection_name,
            )

            results = [
                retriever_pb2.RetrieveResult(
                    doc_id=chunk["doc_id"],
                    paragraph_id=chunk["paragraph_id"],
                    chunk_id=chunk["chunk_id"],
                    text=chunk["text"],
                    pages=chunk["pages"],
                    score=chunk["score"],
                )
                for chunk in search_result.chunks
            ]

            return retriever_pb2.RetrieveResponse(
                results=results,
                success=True,
                error="",
            )

        except Exception as ex:  # noqa: BLE001
            logger.exception("Search failed")
            return retriever_pb2.RetrieveResponse(
                results=[],
                success=False,
                error=str(ex),
            )
