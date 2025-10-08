from __future__ import annotations

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import rag_orchestrator_pb2 as ro_pb2
from protobuf_stubs import rag_orchestrator_pb2_grpc as ro_grpc
from src.grpc.grpc_utils import GrpcTools


class RagOrchestratorGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str, *, target: str) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.target = target
        self.stub = ro_grpc.RagOrchestratorServiceStub(self.channel)


    async def health_check(self) -> bool:
        request = ro_pb2.HealthRequest()
        GrpcTools.validate_proto(request)
        
        try:
            response = await self.stub.Health(
                request,
                timeout=3
            )

            GrpcTools.validate_proto(response)

            return bool(getattr(response, "success", True))

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            return False


    async def rag_search(self, query: str, collection_name: str, top_k: int, max_context_chars: int, summarizer_prompt: str) -> ro_pb2.RagSearchResponse:
        request = ro_pb2.RagSearchRequest(
            query=query,
            collection_name=collection_name,
            top_k=top_k,
            max_context_chars=max_context_chars,
            summarizer_prompt=summarizer_prompt,
        )

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.Search(
                request,
                timeout=120
            )

            GrpcTools.validate_proto(response)

            return response

        except grpc.aio.AioRpcError as ex:
            logger.error(f"RAG search failed: {ex}")
            raise


