from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, List

from loguru import logger
from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc
from src.domain.models import (
    ContextBuilderRequest,
    ContextBuilderResponse,
    ContextChunk,
    HealthStatus,
)
from src.grpc.grpc_utils import GrpcTools

if TYPE_CHECKING:
    import grpc
    from src.services.context_builder_service import ContextBuilderService


class ContextBuilderAPI(context_builder_pb2_grpc.ContextBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, context_builder_service: 'ContextBuilderService') -> None:
        self.context_builder_service = context_builder_service


    @GrpcTools.log_grpc_request('Health')  # type: ignore[misc]
    async def Health(
        self,
        request: context_builder_pb2.HealthRequest,
        context: 'grpc.ServicerContext',
    ) -> context_builder_pb2.HealthResponse:
        try:
            GrpcTools.validate_proto(request, context)

            status: HealthStatus = await asyncio.to_thread(
                self.context_builder_service.get_health_status
            )

            response = context_builder_pb2.HealthResponse(status=status.status)

            GrpcTools.validate_proto(response, context)

            return response

        except Exception as ex:  # noqa: BLE001
            logger.error(f'Health check failed: {ex}')
            return context_builder_pb2.HealthResponse(status='unhealthy')


    @GrpcTools.log_grpc_request('BuildContext')  # type: ignore[misc]
    async def BuildContext(
        self,
        request: context_builder_pb2.BuildContextRequest,
        context: 'grpc.ServicerContext',
    ) -> context_builder_pb2.BuildContextResponse:
        try:
            GrpcTools.validate_proto(request, context)

            chunks: List[ContextChunk] = [
                ContextChunk(
                    doc_id=item.doc_id,
                    paragraph_id=item.paragraph_id,
                    chunk_id=item.chunk_id,
                    text=item.text,
                    pages=list(item.pages),
                    score=float(item.score),
                )
                for item in request.chunks
            ]

            service_request = ContextBuilderRequest(
                chunks=chunks,
                max_context_chars=int(request.max_context_chars),
            )

            result: ContextBuilderResponse = await asyncio.to_thread(
                self.context_builder_service.build_context,
                service_request,
            )

            if not result.success:
                return context_builder_pb2.BuildContextResponse(
                    context_text='',
                    success=False,
                    error=result.error or 'Unknown error',
                )

            return context_builder_pb2.BuildContextResponse(
                context_text=result.context_text,
                success=True,
            )
            
        except Exception as ex:  # noqa: BLE001
            logger.exception('BuildContext failed')
            return context_builder_pb2.BuildContextResponse(
                context_text='',
                success=False,
                error=str(ex),
            )


