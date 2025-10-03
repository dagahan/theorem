from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import grpc
from loguru import logger

from protobuf_stubs import hybrid_embedder_pb2, hybrid_embedder_pb2_grpc
from src.services.hybrid_embedder_service import HybridEmbedderService
from src.grpc.grpc_utils import GrpcTools

from src.pydantic_schemas.hybrid_embedder.models import (
    DenseEmbedBatchRequest,
    DenseEmbedBatchResponse,
    DenseEmbedRequest,
    DenseEmbedResponse,
    HealthStatus,
    SparseEmbedBatchRequest,
    SparseEmbedBatchResponse,
    SparseEmbedRequest,
    SparseEmbedResponse,
)


grpc_tools = GrpcTools()


class HybridEmbedderAPI(hybrid_embedder_pb2_grpc.HybridEmbedderServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self.embedder_service = HybridEmbedderService()


    @staticmethod
    def _to_proto_dense(response: DenseEmbedResponse) -> hybrid_embedder_pb2.DenseEmbedResponse:
        return hybrid_embedder_pb2.DenseEmbedResponse(
            vector=response.vector,
            success=response.success,
            error=response.error or "",
        )


    @staticmethod
    def _to_proto_sparse(response: SparseEmbedResponse) -> hybrid_embedder_pb2.SparseEmbedResponse:
        return hybrid_embedder_pb2.SparseEmbedResponse(
            indices=response.indices,
            values=response.values,
            success=response.success,
            error=response.error or "",
        )


    @grpc_tools.log_grpc_request("Health")
    async def Health(
        self,
        request: hybrid_embedder_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> hybrid_embedder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_status: HealthStatus = await asyncio.to_thread(self.embedder_service.get_health_status)

            response = hybrid_embedder_pb2.HealthResponse(
                status=health_status.status,
                model_id=health_status.model_id,
                dim=health_status.dimensions,
                sparse_vocab_size=health_status.sparse_vocab_size,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Health check failed: {ex}")
            return hybrid_embedder_pb2.HealthResponse(
                status="unhealthy",
                model_id="",
                dim=0,
                sparse_vocab_size=-1
            )


    @grpc_tools.log_grpc_request("DenseEmbed")
    async def DenseEmbed(
        self,
        request: hybrid_embedder_pb2.DenseEmbedRequest,
        context: grpc.ServicerContext,
    ) -> hybrid_embedder_pb2.DenseEmbedResponse:
        try:
            grpc_tools.validate_proto(request, context)

            response: DenseEmbedResponse = await asyncio.to_thread(
                self.embedder_service.dense_embed,
                DenseEmbedRequest(text=request.text),
            )

            proto_response = self._to_proto_dense(response)

            grpc_tools.validate_proto(proto_response, context)

            return proto_response

        except Exception as ex:  # noqa: BLE001
            logger.exception("DenseEmbed failed")
            return hybrid_embedder_pb2.DenseEmbedResponse(
                vector=[],
                success=False,
                error=str(ex)
            )


    @grpc_tools.log_grpc_request("DenseEmbedBatch")
    async def DenseEmbedBatch(
        self,
        request: hybrid_embedder_pb2.DenseEmbedBatchRequest,
        context: grpc.ServicerContext,
    ) -> hybrid_embedder_pb2.DenseEmbedBatchResponse:
        try:
            grpc_tools.validate_proto(request, context)

            response: DenseEmbedBatchResponse = await asyncio.to_thread(
                self.embedder_service.dense_embed_batch,
                DenseEmbedBatchRequest(texts=list(request.texts)),
            )

            items = [self._to_proto_dense(item) for item in response.items]
            proto_response = hybrid_embedder_pb2.DenseEmbedBatchResponse(items=items)

            grpc_tools.validate_proto(proto_response, context)

            if not response.success:
                context.abort(grpc.StatusCode.INTERNAL, response.error or "Batch embedding failed")

            return proto_response

        except grpc.RpcError:
            raise

        except Exception as exc:  # noqa: BLE001
            logger.exception("DenseEmbedBatch failed")
            context.abort(grpc.StatusCode.INTERNAL, str(exc))


    @grpc_tools.log_grpc_request("SparseEmbed")
    async def SparseEmbed(
        self,
        request: hybrid_embedder_pb2.SparseEmbedRequest,
        context: grpc.ServicerContext,
    ) -> hybrid_embedder_pb2.SparseEmbedResponse:
        try:
            grpc_tools.validate_proto(request, context)

            response: SparseEmbedResponse = await asyncio.to_thread(
                self.embedder_service.sparse_embed,
                SparseEmbedRequest(text=request.text),
            )

            proto_response = self._to_proto_sparse(response)
            grpc_tools.validate_proto(proto_response, context)

            return proto_response

        except Exception as ex:  # noqa: BLE001
            logger.exception("SparseEmbed failed")
            return hybrid_embedder_pb2.SparseEmbedResponse(
                indices=[],
                values=[],
                success=False,
                error=str(ex)
            )


    @grpc_tools.log_grpc_request("SparseEmbedBatch")
    async def SparseEmbedBatch(
        self,
        request: hybrid_embedder_pb2.SparseEmbedBatchRequest,
        context: grpc.ServicerContext,
    ) -> hybrid_embedder_pb2.SparseEmbedBatchResponse:
        try:
            grpc_tools.validate_proto(request, context)

            response: SparseEmbedBatchResponse = await asyncio.to_thread(
                self.embedder_service.sparse_embed_batch,
                SparseEmbedBatchRequest(texts=list(request.texts)),
            )

            items = [self._to_proto_sparse(item) for item in response.items]
            proto_response = hybrid_embedder_pb2.SparseEmbedBatchResponse(items=items)

            grpc_tools.validate_proto(proto_response, context)

            if not response.success:
                context.abort(grpc.StatusCode.INTERNAL, response.error or "Batch embedding failed")

            return proto_response

        except grpc.RpcError:
            raise

        except Exception as ex:  # noqa: BLE001
            logger.exception("SparseEmbedBatch failed")
            context.abort(grpc.StatusCode.INTERNAL, str(ex))

