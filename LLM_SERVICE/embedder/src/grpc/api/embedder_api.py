from __future__ import annotations

import grpc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.embedder_service import EmbedderService

from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import EmbeddingRequest, EmbeddingResult, BatchEmbeddingRequest, BatchEmbeddingResult, HealthStatus

grpc_tools = GrpcTools()


class EmbedderAPI(embedder_pb2_grpc.EmbedderServiceServicer):  # type: ignore[misc]
    def __init__(self, embedder_service: "EmbedderService") -> None:
        self.embedder_service = embedder_service


    @grpc_tools.log_grpc_request("Health")
    def Health(
        self,
        request: embedder_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_status: HealthStatus = self.embedder_service.get_health_status()

            response = embedder_pb2.HealthResponse(
                status=health_status.status,
                model_id=health_status.model_id,
                dim=health_status.dimensions,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:
            return embedder_pb2.HealthResponse(status="unhealthy", model_id="", dim=0)


    @grpc_tools.log_grpc_request("Embed")
    def Embed(
        self,
        request: embedder_pb2.EmbedRequest,
        context: grpc.ServicerContext
    ) -> embedder_pb2.EmbedResponse:
        try:
            grpc_tools.validate_proto(request, context)

            embedding_request = EmbeddingRequest(
                text=request.text,
                normalize=request.normalize
            )

            result: EmbeddingResult = self.embedder_service.embed_text(embedding_request)

            if result.success:
                return embedder_pb2.EmbedResponse(
                    vector=result.vector,
                    success=True
                )

            else:
                return embedder_pb2.EmbedResponse(
                    success=False,
                    error=result.error or "Unknown error"
                )

        except Exception as ex:
            return embedder_pb2.EmbedResponse(success=False, error=str(ex))


    @grpc_tools.log_grpc_request("EmbedBatch")
    def EmbedBatch(
        self,
        request: embedder_pb2.EmbedBatchRequest,
        context: grpc.ServicerContext
    ) -> embedder_pb2.EmbedBatchResponse:
        try:
            grpc_tools.validate_proto(request, context)

            batch_request = BatchEmbeddingRequest(
                texts=list(request.texts),
                normalize=request.normalize
            )

            result: BatchEmbeddingResult = self.embedder_service.embed_batch(batch_request)

            if result.success:
                items = [
                    embedder_pb2.EmbedResponse(
                        vector=item.vector,
                        success=item.success
                    )
                    for item in result.results
                ]

                return embedder_pb2.EmbedBatchResponse(items=items)

            else:
                context.abort(grpc.StatusCode.INTERNAL, result.error or "Unknown error")

        except grpc.RpcError:
            raise

        except Exception as ex:
            context.abort(grpc.StatusCode.INTERNAL, str(ex))




