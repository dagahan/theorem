from __future__ import annotations

from typing import TYPE_CHECKING, List

from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import (
    ContextBuilderRequest, ContextBuilderResponse, ContextChunk, HealthStatus
)

if TYPE_CHECKING:
    import grpc
    from src.services.context_builder_service import ContextBuilderService

grpc_tools = GrpcTools()


class ContextBuilderAPI(context_builder_pb2_grpc.ContextBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, context_builder_service: "ContextBuilderService") -> None:
        self.context_builder_service = context_builder_service


    @grpc_tools.log_grpc_request("Health")   # type: ignore[misc]
    def Health(self, request: context_builder_pb2.HealthRequest, context: grpc.ServicerContext) -> context_builder_pb2.HealthResponse:
        grpc_tools.validate_proto(request, context)

        status: HealthStatus = self.context_builder_service.get_health_status()
        response = context_builder_pb2.HealthResponse(status=status.status, version=status.version)

        grpc_tools.validate_proto(response, context)

        return response


    @grpc_tools.log_grpc_request("BuildContext")   # type: ignore[misc]
    def BuildContext(self, request: context_builder_pb2.BuildContextRequest, context: grpc.ServicerContext) -> context_builder_pb2.BuildContextResponse:
        grpc_tools.validate_proto(request, context)

        chunks: List[ContextChunk] = [
            ContextChunk(
                doc_id=it.doc_id,
                paragraph_id=it.paragraph_id,
                chunk_id=it.chunk_id,
                text=it.text,
                pages=list(it.pages),
                score=float(it.score)
            )

            for it in request.chunks
        ]

        service_request = ContextBuilderRequest(
            chunks=chunks,
            max_context_chars=int(request.max_context_chars)
        )

        result: ContextBuilderResponse = self.context_builder_service.build_context(service_request)

        if not result.success:
            return context_builder_pb2.BuildContextResponse(
                context_text="",
                success=False,
                error=result.error or "Unknown error"
            )

        return context_builder_pb2.BuildContextResponse(
            context_text=result.context_text,
            success=True
        )




