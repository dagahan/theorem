from __future__ import annotations
import grpc
from loguru import logger

from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import ContextBuilderRequest, ContextBuilderResponse


class ContextBuilderGrpcClient:
    def __init__(self, channel: grpc.Channel, service_name: str) -> None:
        self.channel = channel
        self.service_name = service_name
        self.stub = context_builder_pb2_grpc.ContextBuilderServiceStub(self.channel)


    async def health_check(self) -> bool:
        request = context_builder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)

        try:
            response = self.stub.Health(request, timeout=3)
            GrpcTools.validate_proto(response)
            return bool(response.status == "healthy")

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            return False


    async def build_context(
        self,
        request: ContextBuilderRequest
    ) -> ContextBuilderResponse:
        chunks_pb = [
            context_builder_pb2.ContextChunk(
                doc_id=c.doc_id,
                paragraph_id=c.paragraph_id,
                chunk_id=c.chunk_id,
                text=c.text,
                pages=c.pages,
                score=c.score
            )
            for c in request.chunks
        ]

        request = context_builder_pb2.BuildContextRequest(
            chunks=chunks_pb,
            max_context_chars=request.max_context_chars
        )

        GrpcTools.validate_proto(request)

        try:
            response = self.stub.BuildContext(request, timeout=30)

            if not response.success:
                return ContextBuilderResponse(
                    context_text="",
                    success=False,
                    error=response.error or "context_builder error"
                )

            GrpcTools.validate_proto(response)

            return ContextBuilderResponse(context_text=response.context_text, success=True)

        except grpc.RpcError as ex:
            logger.error(f"BuildContext failed: {ex}")
            return ContextBuilderResponse(context_text="", success=False, error=str(ex))


