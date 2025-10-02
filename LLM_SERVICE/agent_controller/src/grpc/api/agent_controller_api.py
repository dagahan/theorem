from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from protobuf_stubs import agent_controller_pb2, agent_controller_pb2_grpc
from src.domain.models import ServiceStatus, UserQuery
from src.grpc.grpc_utils import GrpcTools


if TYPE_CHECKING:
    import grpc
    from src.services.orchestrator import LLMGraphOrchestrator


grpc_tools = GrpcTools()


class AgentControllerAPI(agent_controller_pb2_grpc.AgentControllerServiceServicer):  # type: ignore[misc]
    def __init__(self, orchestrator: 'LLMGraphOrchestrator') -> None:
        self.orchestrator = orchestrator


    @grpc_tools.log_grpc_request('Health')
    async def Health(
        self,
        request: agent_controller_pb2.HealthRequest,
        context: 'grpc.ServicerContext',
    ) -> agent_controller_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_check = await self.orchestrator.health_check()
            
            components = [
                agent_controller_pb2.ComponentStatus(
                    name=component.name,
                    status=component.status.value,
                    details=component.details or '',
                )
                for component in health_check.components
            ]

            response = agent_controller_pb2.HealthResponse(
                status=health_check.overall_status.value,
                components=components,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:  # noqa: BLE001
            logger.error(f'Health check failed: {ex}')
            return agent_controller_pb2.HealthResponse(
                status=ServiceStatus.UNHEALTHY.value,
                components=[
                    agent_controller_pb2.ComponentStatus(
                        name='agent_controller',
                        status=ServiceStatus.UNHEALTHY.value,
                        details=str(ex),
                    )
                ],
            )


    @grpc_tools.log_grpc_request('AnswerQuestion')
    async def AnswerQuestion(
        self,
        request: agent_controller_pb2.QuestionRequest,
        context: 'grpc.ServicerContext',
    ) -> agent_controller_pb2.QuestionResponse:
        try:
            grpc_tools.validate_proto(request, context)

            question_request = UserQuery(
                raw_text=request.raw_text,
                agent_name=request.agent_name,
                stream=request.stream,
            )

            question_response = await self.orchestrator.answer_question(
                query=question_request,
                run_id=request.run_id or None,
            )

            response = agent_controller_pb2.QuestionResponse(
                answer=question_response.answer,
                success=question_response.success,
                error=question_response.error or '',
            )

            grpc_tools.validate_proto(response, context)

            return response

        except asyncio.TimeoutError as exc:
            message = str(exc) or 'Question processing timed out'
            logger.warning(f'Answer question timed out: {message}')
            return agent_controller_pb2.QuestionResponse(
                answer='',
                success=False,
                error=message,
            )
            
        except Exception as ex:  # noqa: BLE001
            logger.exception('Answer question failed')
            return agent_controller_pb2.QuestionResponse(
                answer='',
                success=False,
                error=str(ex),
            )
