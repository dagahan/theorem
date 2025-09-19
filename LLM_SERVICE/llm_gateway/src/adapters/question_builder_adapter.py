from __future__ import annotations

import grpc
from loguru import logger
from src.core.utils import EnvTools
from src.domain.models import QuestionBuilderRequest, QuestionBuilderResponse
from protobuf_stubs import question_builder_pb2, question_builder_pb2_grpc


class QuestionBuilderAdapter:
    def __init__(self) -> None:
        self.host = EnvTools.get_service_host("question_builder")
        self.port = int(EnvTools.get_service_grpc_port("question_builder"))
        self.addr = f"{self.host}:{self.port}"
        self.channel = grpc.insecure_channel(self.addr)
        self.stub = question_builder_pb2_grpc.QuestionBuilderServiceStub(self.channel)


    async def process_question(
        self,
        request: QuestionBuilderRequest
    ) -> QuestionBuilderResponse:
        try:
            grpc_request = question_builder_pb2.ProcessQuestionRequest(
                raw_text=request.raw_text
            )
            
            grpc_response = self.stub.ProcessQuestion(grpc_request, timeout=60.0)
            
            return QuestionBuilderResponse(
                original_question=grpc_response.original_question,
                expanded_question=grpc_response.expanded_question,
                expanded_question_semantic_parts=list(grpc_response.expanded_question_semantic_parts),
                success=grpc_response.success,
                error=grpc_response.error if grpc_response.error else None
            )
            
        except Exception as ex:
            logger.error(f"QuestionBuilder request failed: {ex}")
            return QuestionBuilderResponse(
                original_question=request.raw_text,
                expanded_question=request.raw_text,
                expanded_question_semantic_parts=[request.raw_text],
                success=False,
                error=str(ex)
            )


    async def health_check(self) -> bool:
        try:
            grpc_request = question_builder_pb2.HealthRequest()
            grpc_response = self.stub.Health(grpc_request, timeout=5.0)
            return bool(grpc_response.status == "healthy")
            
        except Exception as ex:
            logger.error(f"QuestionBuilder health check failed: {ex}")
            return False


