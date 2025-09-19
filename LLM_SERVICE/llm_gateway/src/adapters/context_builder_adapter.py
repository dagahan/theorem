from __future__ import annotations

import grpc
from loguru import logger

from src.core.utils import EnvTools
from src.domain.models import (
    ContextBuilderRequest,
    ContextBuilderResponse,
)

from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc


class ContextBuilderAdapter:
    def __init__(self) -> None:
        host: str = EnvTools.get_service_host("context_builder")
        port: str = EnvTools.get_service_grpc_port("context_builder")
        self._channel = grpc.insecure_channel(f"{host}:{port}")
        self._stub = context_builder_pb2_grpc.ContextBuilderServiceStub(self._channel)


    async def build_context(self, request: ContextBuilderRequest) -> ContextBuilderResponse:
        try:
            chunks_pb = [
                context_builder_pb2.ContextChunk(
                    doc_id=c.doc_id,
                    paragraph_id=c.paragraph_id,
                    chunk_id=c.chunk_id,
                    text=c.text,
                    pages=c.pages,
                    score=c.score,
                )
                for c in request.chunks
            ]

            grpc_request = context_builder_pb2.BuildContextRequest(
                chunks=chunks_pb,
                max_context_chars=request.max_context_chars,
            )

            response = self._stub.BuildContext(grpc_request, timeout=30.0)

            if not response.success:
                msg = f"Context builder service returned error: {response.error}"
                logger.error(msg)
                return ContextBuilderResponse(context_text="", success=False, error=msg)

            return ContextBuilderResponse(context_text=response.context_text, success=True)

        except Exception as ex:
            logger.error(f"Context builder adapter failed: {ex}")
            return ContextBuilderResponse(context_text="", success=False, error=str(ex))


    async def health_check(self) -> bool:
        try:
            resp = self._stub.Health(context_builder_pb2.HealthRequest(), timeout=5.0)
            return bool(resp.status == "healthy")
        except Exception:
            return False


