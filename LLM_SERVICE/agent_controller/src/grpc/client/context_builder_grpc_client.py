from __future__ import annotations

import asyncio

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import context_builder_pb2, context_builder_pb2_grpc
from src.core.timeouts import TimeoutTools
from src.domain.models import ContextBuilderRequest, ContextBuilderResponse
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
            response = await self.stub.Health(request, timeout=timeout_sec)
            
            GrpcTools.validate_proto(response)

            return bool(response.status == 'healthy')

        except grpc.RpcError as exc:  # includes aio errors
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
                score=chunk.score
            )
            for chunk in request.chunks
        ]

        request_pb = context_builder_pb2.BuildContextRequest(
            chunks=chunks_pb,
            max_context_chars=request.max_context_chars
        )

        GrpcTools.validate_proto(request_pb)
        
        timeout_sec = TimeoutTools.resolve_node_rpc_timeout()

        try:
            if timeout_sec is not None:
                response = await self.stub.BuildContext(
                    request_pb,
                    timeout=timeout_sec
                )

            else:
                response = await self.stub.BuildContext(request_pb)

        except grpc.aio.AioRpcError as ex:
            status = ex.code()

            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} BuildContext deadline exceeded for {self.target}"
                )

                raise asyncio.TimeoutError('context_builder timeout') from ex

            return ContextBuilderResponse(
                context_text='',
                success=False,
                error=str(ex)
            )

        except asyncio.CancelledError as ex:
            if timeout_sec is None:
                raise

            message = (
                f"{self.service_name} BuildContext timed out after {timeout_sec:.1f}s "
                f"for {self.target}"
            )

            logger.warning(message)

            raise asyncio.TimeoutError(message) from ex

        except grpc.RpcError as ex:
            return ContextBuilderResponse(
                context_text='',
                success=False,
                error=str(ex)
            )

        if not response.success:
            return ContextBuilderResponse(
                context_text='',
                success=False,
                error=response.error or 'context_builder error'
            )

        GrpcTools.validate_proto(response)

        return ContextBuilderResponse(
            context_text=response.context_text,
            success=True
        )
    


