from __future__ import annotations
import grpc
from loguru import logger
from src.core.utils import EnvTools
from src.domain.models import RetrieveRequest, RetrieveResponse, RetrieveResult
from protobuf_stubs import retriever_pb2, retriever_pb2_grpc

class RetrieverAdapter:
    def __init__(self) -> None:
        self.host = EnvTools.get_service_host("retriever")
        self.port = EnvTools.get_service_grpc_port("retriever")
        self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
        self.client = retriever_pb2_grpc.RetrieverServiceStub(self.channel)


    async def retrieve_context(
        self,
        request: RetrieveRequest
    ) -> RetrieveResponse:
        try:
            grpc_request = retriever_pb2.RetrieveRequest(
                query=request.query,
                collection_name=request.collection_name
            )
            
            grpc_response = self.client.Retrieve(grpc_request, timeout=60.0)
            
            if not grpc_response.success:
                error_msg = f"Retriever service returned error: {grpc_response.error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            results = []
            
            for result in grpc_response.results:
                results.append(RetrieveResult(
                    doc_id=result.doc_id,
                    text=result.text,
                    score=result.score,
                    pages=list(result.pages),
                    paragraph_id=result.paragraph_id,
                    chunk_id=result.chunk_id
                ))
            
            return RetrieveResponse(
                results=results,
                success=True
            )
            
        except Exception as ex:
            return RetrieveResponse(
                results=[],
                success=False,
                error=str(ex)
            )


    async def health_check(self) -> bool:
        try:
            grpc_request = retriever_pb2.HealthRequest()
            grpc_response = self.client.Health(grpc_request, timeout=5.0)
            return bool(grpc_response.status == "healthy")

        except Exception:
            return False


