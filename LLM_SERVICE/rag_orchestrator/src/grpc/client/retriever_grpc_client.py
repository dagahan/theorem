from __future__ import annotations

import grpc.aio  # type: ignore[import-not-found]
from loguru import logger

from protobuf_stubs import retriever_pb2 as r_pb2
from protobuf_stubs import retriever_pb2_grpc as r_grpc
from src.grpc.grpc_utils import GrpcTools


class RetrieverGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str, *, target: str) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.target = target
        self.stub = r_grpc.RetrieverServiceStub(self.channel)


    async def retrieve(
        self,
        question: str,
        collection_name: str,
        top_k: int = 10
    ) -> r_pb2.RetrieveResponse:
        request = r_pb2.RetrieveRequest(
            question=question,
            collection_name=collection_name
        )

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.Retrieve(
                request,
                timeout=60
            )

            GrpcTools.validate_proto(response)
            
            return response

        except grpc.aio.AioRpcError as ex:
            logger.error(f"Retriever failed: {ex}")
            raise


