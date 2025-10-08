from __future__ import annotations

from typing import TYPE_CHECKING

import grpc  # type: ignore[import-untyped]
from loguru import logger

from protobuf_stubs import llm_gateway_pb2, llm_gateway_pb2_grpc
from src.grpc.grpc_utils import GrpcTools


if TYPE_CHECKING:
    from grpc import ServicerContext
    from src.grpc.client.agent_controller_grpc_client import AgentControllerGrpcClient


grpc_tools = GrpcTools()


class LLMGatewayAPI(llm_gateway_pb2_grpc.LLMGatewayServiceServicer):  # type: ignore[misc]
    def __init__(self, agent_client: AgentControllerGrpcClient) -> None:
        self.agent_client = agent_client


    @grpc_tools.log_grpc_request('Health')
    async def Health(
        self,
        request: llm_gateway_pb2.HealthRequest,
        context: 'ServicerContext',
    ) -> llm_gateway_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)
            agent_response = await self.agent_client.health_check()

            downstream = [
                llm_gateway_pb2.ComponentStatus(
                    name=component.name,
                    status=component.status,
                    details=component.details,
                )
                for component in agent_response.components
            ]

            unhealthy_components = [
                f"{component.name}:{component.status}"
                for component in downstream
                if component.status != 'healthy'
            ]
            agent_details = ', '.join(unhealthy_components) if unhealthy_components else ''

            response = llm_gateway_pb2.HealthResponse(
                status=agent_response.status,
                agent_controller=llm_gateway_pb2.ComponentStatus(
                    name='agent_controller',
                    status=agent_response.status,
                    details=agent_details,
                ),
                downstream_components=downstream,
            )

            grpc_tools.validate_proto(response, context)
            
            return response

        except grpc.RpcError as ex:
            logger.error(f'Agent controller health check RPC failed: {ex}')

        except Exception as ex:  # noqa: BLE001
            logger.error(f'Agent controller health check failed: {ex}')

        return llm_gateway_pb2.HealthResponse(
            status='unhealthy',
            agent_controller=llm_gateway_pb2.ComponentStatus(
                name='agent_controller',
                status='unhealthy',
                details='agent controller unreachable',
            ),
            downstream_components=[],
        )


    @grpc_tools.log_grpc_request('Question')
    async def Question(
        self,
        request: llm_gateway_pb2.QuestionRequest,
        context: 'ServicerContext',
    ) -> llm_gateway_pb2.QuestionResponse:
        try:
            grpc_tools.validate_proto(request, context)

            agent_response = await self.agent_client.answer_question(
                question=request.question,
                stream=request.stream,
                agent_name=request.agent_name,
            )

            response = llm_gateway_pb2.QuestionResponse(
                answer=agent_response.answer,
                success=agent_response.success,
                error=agent_response.error,
            )

            grpc_tools.validate_proto(response, context)
            return response
        except grpc.RpcError as ex:
            logger.error(f'Agent controller question RPC failed: {ex}')
            return llm_gateway_pb2.QuestionResponse(
                answer='',
                success=False,
                error='agent controller unavailable',
            )
        except Exception as ex:  # noqa: BLE001
            logger.exception('Answer question failed')
            return llm_gateway_pb2.QuestionResponse(
                answer='',
                success=False,
                error=str(ex),
            )

