from __future__ import annotations

import asyncio

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import question_builder_pb2, question_builder_pb2_grpc
from src.core.timeouts import TimeoutTools
from src.domain.models import QuestionBuilderRequest, QuestionBuilderResponse
from src.grpc.grpc_utils import GrpcTools


class QuestionBuilderGrpcClient:
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
        self.stub = question_builder_pb2_grpc.QuestionBuilderServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call('question_builder', 'Health')
    async def health_check(self) -> bool:
        request = question_builder_pb2.HealthRequest()

        GrpcTools.validate_proto(request)

        timeout_sec = TimeoutTools.get_health_check_timeout()

        try:
            response = await self.stub.Health(
                request,
                timeout=timeout_sec
            )

            GrpcTools.validate_proto(response)

            return bool(response.status == 'healthy')

        except grpc.RpcError as ex:
            return False


    @GrpcTools.log_grpc_client_call('question_builder', 'ProcessQuestion')
    async def process_question(
        self,
        request: QuestionBuilderRequest
    ) -> QuestionBuilderResponse:
        request_pb = question_builder_pb2.ProcessQuestionRequest(
            raw_text=request.raw_text
        )

        GrpcTools.validate_proto(request_pb)

        timeout_sec = TimeoutTools.resolve_node_rpc_timeout()

        try:
            if timeout_sec is not None:
                response = await self.stub.ProcessQuestion(
                    request_pb,
                    timeout=timeout_sec
                )

            else:
                response = await self.stub.ProcessQuestion(request_pb)

        except grpc.aio.AioRpcError as ex:
            status = ex.code()

            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} ProcessQuestion deadline exceeded for {self.target}"
                )

                raise asyncio.TimeoutError('question_builder timeout') from ex

            return QuestionBuilderResponse(
                original_question=request.raw_text,
                expanded_question=request.raw_text,
                expanded_question_semantic_parts=[request.raw_text],
                success=False,
                error=str(ex)
            )

        except asyncio.CancelledError as ex:
            if timeout_sec is None:
                raise

            message = (
                f"{self.service_name} ProcessQuestion timed out after {timeout_sec:.1f}s "
                f"for {self.target}"
            )

            logger.warning(message)
            
            raise asyncio.TimeoutError(message) from ex

        except grpc.RpcError as ex:
            return QuestionBuilderResponse(
                original_question=request.raw_text,
                expanded_question=request.raw_text,
                expanded_question_semantic_parts=[request.raw_text],
                success=False,
                error=str(ex)
            )

        if not response.success:
            return QuestionBuilderResponse(
                original_question=request.raw_text,
                expanded_question=request.raw_text,
                expanded_question_semantic_parts=[request.raw_text],
                success=False,
                error=response.error or 'question_builder error'
            )

        GrpcTools.validate_proto(response)
        
        return QuestionBuilderResponse(
            original_question=response.original_question,
            expanded_question=response.expanded_question,
            expanded_question_semantic_parts=list(response.expanded_question_semantic_parts),
            success=True
        )

