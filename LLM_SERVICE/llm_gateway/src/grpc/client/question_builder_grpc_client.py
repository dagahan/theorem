from __future__ import annotations
import grpc.aio
from loguru import logger

from protobuf_stubs import question_builder_pb2, question_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import QuestionBuilderRequest, QuestionBuilderResponse


class QuestionBuilderGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str) -> None:
        self.channel = channel
        self.service_name = service_name
        self.stub = question_builder_pb2_grpc.QuestionBuilderServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call("question_builder", "Health")
    async def health_check(self) -> bool:
        request = question_builder_pb2.HealthRequest()

        GrpcTools.validate_proto(request)

        try:
            resp = await self.stub.Health(request, timeout=3)
            GrpcTools.validate_proto(resp)
            return bool(resp.status == "healthy")

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            return False


    @GrpcTools.log_grpc_client_call("question_builder", "ProcessQuestion")
    async def process_question(
        self,
        request: QuestionBuilderRequest
    ) -> QuestionBuilderResponse:
        request = question_builder_pb2.ProcessQuestionRequest(raw_text=request.raw_text)

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.ProcessQuestion(request, timeout=30)

            if not response.success:
                return QuestionBuilderResponse(
                    original_question=request.raw_text,
                    expanded_question=request.raw_text,
                    expanded_question_semantic_parts=[request.raw_text],
                    success=False,
                    error=response.error or "question_builder error"
                )

            GrpcTools.validate_proto(response)

            return QuestionBuilderResponse(
                original_question=response.original_question,
                expanded_question=response.expanded_question,
                expanded_question_semantic_parts=list(response.expanded_question_semantic_parts),
                success=True
            )

        except grpc.RpcError as ex:
            logger.error(f"ProcessQuestion failed: {ex}")
            return QuestionBuilderResponse(
                original_question=request.raw_text,
                expanded_question=request.raw_text,
                expanded_question_semantic_parts=[request.raw_text],
                success=False,
                error=str(ex)
            )

