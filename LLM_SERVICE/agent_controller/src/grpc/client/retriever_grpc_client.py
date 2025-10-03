
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import retriever_pb2, retriever_pb2_grpc
from src.core.timeouts import TimeoutTools
from src.grpc.grpc_utils import GrpcTools
from src.pydantic_schemas.agent_controller import RetrieveResponse as DomainRetrieveResponse, RetrieveResult

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import RetrieveRequest, RetrieveResponse


class RetrieverGrpcClient:
    def __init__(
        self,
        channel: grpc.aio.Channel,
        service_name: str,
        *,
        target: str,
    ) -> None:
        self.channel = channel
        self.service_name = service_name
        self.target = target
        self.stub = retriever_pb2_grpc.RetrieverServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call('retriever', 'Health')
    async def health_check(self) -> retriever_pb2.HealthResponse:
        request = retriever_pb2.HealthRequest()

        GrpcTools.validate_proto(request)

        timeout_sec = TimeoutTools.get_health_check_timeout()

        response = await self.stub.Health(
            request,
            timeout=timeout_sec
        )

        GrpcTools.validate_proto(response)

        return response


    @GrpcTools.log_grpc_client_call('retriever', 'Retrieve')
    async def retrieve_context(
        self,
        request: RetrieveRequest
    ) -> RetrieveResponse:
        request_pb = retriever_pb2.RetrieveRequest(
            question=request.question,
            collection_name=request.collection_name
        )

        GrpcTools.validate_proto(request_pb)

        timeout_sec = TimeoutTools.resolve_node_rpc_timeout()

        try:
            if timeout_sec is not None:
                response = await self.stub.Retrieve(
                    request_pb,
                    timeout=timeout_sec
                )

            else:
                response = await self.stub.Retrieve(request_pb)

        except grpc.aio.AioRpcError as ex:
            status = ex.code()

            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} Retrieve deadline exceeded for {self.target}"
                )

                raise asyncio.TimeoutError('retriever timeout') from ex

            raise

        except asyncio.CancelledError as ex:
            if timeout_sec is None:
                raise

            message = (
                f"{self.service_name} Retrieve timed out after {timeout_sec:.1f}s "
                f"for {self.target}"
            )

            logger.warning(message)
            
            raise asyncio.TimeoutError(message) from ex

        except grpc.RpcError as ex:
            raise

        GrpcTools.validate_proto(response)

        results = [
            RetrieveResult(
                doc_id=item.doc_id,
                text=item.text,
                score=item.score,
                pages=list(item.pages),
                paragraph_id=item.paragraph_id,
                chunk_id=item.chunk_id
            )
            for item in response.results
        ]

        return DomainRetrieveResponse(
            results=results,
            success=response.success,
            error=response.error or None
        )


