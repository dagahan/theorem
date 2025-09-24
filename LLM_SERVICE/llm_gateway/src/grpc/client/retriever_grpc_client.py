from __future__ import annotations
from typing import List
import grpc.aio
from loguru import logger

from protobuf_stubs import retriever_pb2, retriever_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import RetrieveRequest, RetrieveResult, RetrieveResponse


class RetrieverGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str) -> None:
        self.channel = channel
        self.service_name = service_name
        self.stub = retriever_pb2_grpc.RetrieverServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call("retriever", "Health")
    async def health_check(self) -> RetrieveResponse:
        request = retriever_pb2.HealthRequest()

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.Health(request, timeout=3)

            GrpcTools.validate_proto(response)

            ok = (response.status == "healthy")

            return RetrieveResponse(
                results=[],
                success=ok,
                error=None if ok else "unhealthy"
            )

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            return RetrieveResponse(results=[], success=False, error=str(ex))


    @GrpcTools.log_grpc_client_call("retriever", "Retrieve")
    async def retrieve_context(
        self,
        request: RetrieveRequest
    ) -> RetrieveResponse:

        pb = retriever_pb2.RetrieveRequest(
            question=request.question,
            collection_name=request.collection_name
        )

        GrpcTools.validate_proto(pb)

        try:
            response = await self.stub.Retrieve(pb, timeout=60)

            if not response.success:
                return RetrieveResponse(
                    results=[],
                    success=False,
                    error=response.error or "retriever error"
                )

            GrpcTools.validate_proto(response)

            results: List[RetrieveResult] = [
                RetrieveResult(
                    doc_id=r.doc_id,
                    text=r.text,
                    score=r.score,
                    pages=list(r.pages),
                    paragraph_id=r.paragraph_id,
                    chunk_id=r.chunk_id
                )
                for r in response.results
            ]

            return RetrieveResponse(
                results=results,
                success=True
            )

        except grpc.RpcError as ex:
            logger.error(f"Retrieve failed: {ex}")
            return RetrieveResponse(results=[], success=False, error=str(ex))
