from __future__ import annotations

import asyncio

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc

from src.core.timeouts import TimeoutTools
from src.pydantic_schemas.agent_controller import (
    ContextBuilderRequest,
    ContextBuilderResponse,
    ContextChunk,
    ContextDigestItem,
)
from src.grpc.grpc_utils import GrpcTools


class ContextBuilderGrpcClient:
    def __init__(
        self,
        channel: grpc.aio.Channel,
        service_name: str,
        *,
        target: str
    ) -> None:
        self.channel = channel
        self.service_name = service_name
        self.target = target
        self.stub = context_builder_pb2_grpc.ContextBuilderServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call('context_builder', 'Health')
    async def health_check(self) -> bool:
        request = context_builder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)

        timeout_sec = TimeoutTools.get_health_check_timeout()

        try:
            response = await self.stub.Health(
                request,
                timeout=timeout_sec
            )

            GrpcTools.validate_proto(response)

            return response.status == 'healthy'  # type: ignore

        except grpc.RpcError:
            return False


    @GrpcTools.log_grpc_client_call('context_builder', 'BuildContext')
    async def build_context(
        self,
        request: ContextBuilderRequest
    ) -> ContextBuilderResponse:
        chunks_pb = [
            context_builder_pb2.ContextChunk(
                doc_id=chunk.doc_id,
                paragraph_id=chunk.paragraph_id,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                pages=chunk.pages,
                score=chunk.score,
            )
            for chunk in request.chunks
        ]

        request_pb = context_builder_pb2.BuildContextRequest(
            chunks=chunks_pb,
            max_context_chars=request.max_context_chars,
            summarizer_prompt=request.summarizer_prompt,
        )

        GrpcTools.validate_proto(request_pb)

        node_timeout = TimeoutTools.get_timeout('CONTEXT_BUILDER_NODE_TIMEOUT_SEC', 180.0)
        timeout_sec = TimeoutTools.resolve_node_rpc_timeout(node_timeout)

        try:
            if timeout_sec is not None:
                response = await self.stub.BuildContext(
                    request_pb,
                    timeout=timeout_sec,
                )

            else:
                response = await self.stub.BuildContext(request_pb)

        except grpc.aio.AioRpcError as ex:
            status = ex.code()

            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} BuildContext deadline exceeded for {self.target}"
                )

                raise TimeoutError('context_builder timeout') from ex

            return ContextBuilderResponse(digests=[], success=False, error=str(ex))

        except asyncio.CancelledError as ex:
            if timeout_sec is None:
                raise

            message = (
                f"{self.service_name} BuildContext timed out after {timeout_sec:.1f}s "
                f"for {self.target}"
            )

            logger.warning(message)

            raise TimeoutError(message) from ex

        except grpc.RpcError as ex:
            return ContextBuilderResponse(
                digests=[],
                success=False,
                error=str(ex)
            )

        if response is None:
            return ContextBuilderResponse(
                digests=[],
                success=False,
                error='context_builder returned empty response',
            )

        if not response.success:
            return ContextBuilderResponse(
                digests=[],
                success=False,
                error=response.error or 'context_builder error',
            )

        GrpcTools.validate_proto(response)

        digests = [
            ContextDigestItem(
                title=item.title,
                summary=item.summary,
                source_chunk=ContextChunk(
                    doc_id=item.source_chunk.doc_id,
                    paragraph_id=item.source_chunk.paragraph_id,
                    chunk_id=item.source_chunk.chunk_id,
                    text=item.source_chunk.text,
                    pages=list(item.source_chunk.pages),
                    score=item.source_chunk.score,
                ),
            )
            for item in response.digests
        ]

        return ContextBuilderResponse(
            digests=digests,
            success=True,
        )
