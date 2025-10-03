from __future__ import annotations

from typing import TYPE_CHECKING, List

from loguru import logger

from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc
from src.pydantic_schemas.context_builder import ContextBuilderRequest, ContextChunk
from src.grpc.grpc_utils import GrpcTools

if TYPE_CHECKING:
    import grpc
    from src.pydantic_schemas.context_builder import ContextBuilderResponse
    from src.services.context_builder_service import ContextBuilderService


class ContextBuilderAPI(context_builder_pb2_grpc.ContextBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, context_builder_service: ContextBuilderService) -> None:
        self.context_builder_service = context_builder_service


    @GrpcTools.log_grpc_request('Health')  # type: ignore[misc]
    async def Health(
        self,
        request: context_builder_pb2.HealthRequest,
        context: 'grpc.ServicerContext',
    ) -> context_builder_pb2.HealthResponse:
        try:
            GrpcTools.validate_proto(request, context)

            status = self.context_builder_service.get_health_status()

            response = context_builder_pb2.HealthResponse(status=status.status)

            GrpcTools.validate_proto(response, context)

            return response

        except Exception as exc:  # noqa: BLE001
            logger.error('Health check failed: %s', exc)
            return context_builder_pb2.HealthResponse(status='unhealthy')


    @GrpcTools.log_grpc_request('BuildContext')  # type: ignore[misc]
    async def BuildContext(
        self,
        request: context_builder_pb2.BuildContextRequest,
        context: 'grpc.ServicerContext',
    ) -> context_builder_pb2.BuildContextResponse:
        try:
            logger.info(f"BuildContext request: {len(request.chunks)} chunks, max_chars={request.max_context_chars}")
            GrpcTools.validate_proto(request, context)
            logger.info("BuildContext request validation passed")

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
                summarizer_prompt=request.summarizer_prompt,
            )

            result = await self.context_builder_service.build_context(service_request)

            if not result.success:
                return context_builder_pb2.BuildContextResponse(
                    digests=[],
                    success=False,
                    error=result.error or 'context_builder error',
                )

            response = context_builder_pb2.BuildContextResponse(
                digests=[
                    context_builder_pb2.DigestItem(
                        title=item.title,
                        summary=item.summary,
                        source_chunk=context_builder_pb2.ContextChunk(
                            doc_id=item.source_chunk.doc_id,
                            paragraph_id=item.source_chunk.paragraph_id,
                            chunk_id=item.source_chunk.chunk_id,
                            text=item.source_chunk.text,
                            pages=list(item.source_chunk.pages),
                            score=item.source_chunk.score,
                        ),
                    )
                    for item in result.digests
                ],
                success=True,
            )

            GrpcTools.validate_proto(response, context)
            
            return response

        except Exception as ex:  # noqa: BLE001
            logger.error(f"BuildContext failed: {ex}")
            return context_builder_pb2.BuildContextResponse(
                digests=[],
                success=False,
                error=str(ex),
            )
