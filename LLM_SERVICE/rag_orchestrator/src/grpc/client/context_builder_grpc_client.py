from __future__ import annotations

import grpc.aio  # type: ignore[import-not-found]
from loguru import logger

from protobuf_stubs import context_builder_pb2 as c_pb2
from protobuf_stubs import context_builder_pb2_grpc as c_grpc
from src.grpc.grpc_utils import GrpcTools


class ContextBuilderGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str, *, target: str) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.target = target
        self.stub = c_grpc.ContextBuilderServiceStub(self.channel)


    async def build_context(
        self,
        chunks: list[c_pb2.ContextChunk],
        max_context_chars: int,
        summarizer_prompt: str
    ) -> c_pb2.ContextBuilderResponse:
        request = c_pb2.BuildContextRequest(
            chunks=chunks,
            max_context_chars=max_context_chars,
            summarizer_prompt=summarizer_prompt
        )

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.BuildContext(
                request,
                timeout=120
            )

            GrpcTools.validate_proto(response)

            return response

        except grpc.aio.AioRpcError as ex:
            logger.error(f"ContextBuilder failed: {ex}")
            raise


            