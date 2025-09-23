from __future__ import annotations
from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    import grpc
    from src.services.orchestrator import LLMGraphOrchestrator

from protobuf_stubs import llm_gateway_pb2, llm_gateway_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import UserQuery, RetrieveRequest, ServiceStatus

grpc_tools = GrpcTools()

class LLMGatewayAPI(llm_gateway_pb2_grpc.LLMGatewayServiceServicer):  # type: ignore[misc]
    def __init__(self, orchestrator: "LLMGraphOrchestrator") -> None:
        self.orchestrator = orchestrator


    @grpc_tools.log_grpc_request("Health")
    async def Health(self, request: llm_gateway_pb2.HealthRequest, context: grpc.ServicerContext) -> llm_gateway_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)
            
            health_check = await self.orchestrator.health_check()
            
            response = llm_gateway_pb2.HealthResponse(
                status=health_check.overall_status.value,
                llm_status=health_check.llm_status.value,
                retriever_status=health_check.retriever_status.value,
                embedder_status=health_check.embedder_status.value
            )
            
            grpc_tools.validate_proto(response, context)

            return response
            
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return llm_gateway_pb2.HealthResponse(
                status=ServiceStatus.UNHEALTHY.value,
                llm_status=ServiceStatus.UNKNOWN.value,
                retriever_status=ServiceStatus.UNKNOWN.value,
                embedder_status=ServiceStatus.UNKNOWN.value
            )


    @grpc_tools.log_grpc_request("Question")
    async def Question(self, request: llm_gateway_pb2.QuestionRequest, context: grpc.ServicerContext) -> llm_gateway_pb2.QuestionResponse:
        try:
            grpc_tools.validate_proto(request, context)
            
            question_request = UserQuery(
                raw_text=request.raw_text,
                stream=request.stream
            )
            
            question_response = await self.orchestrator.answer_question(question_request)
            
            response = llm_gateway_pb2.QuestionResponse(
                answer=question_response.answer,
                success=question_response.success,
                error=question_response.error or ""
            )
            
            grpc_tools.validate_proto(response, context)
            return response
            
        except Exception as ex:
            logger.exception("Answer question failed")
            return llm_gateway_pb2.QuestionResponse(
                answer="",
                success=False,
                error=str(ex)
            )

    