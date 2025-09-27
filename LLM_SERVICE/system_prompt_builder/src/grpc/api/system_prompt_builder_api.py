from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from protobuf_stubs import system_prompt_builder_pb2, system_prompt_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools


if TYPE_CHECKING:
    import grpc
    from src.domain.models import BuildSystemPromptResponse, HealthStatus
    from src.services.policy_builder_service import SystemPromptBuilderService


class SystemPromptBuilderAPI(system_prompt_builder_pb2_grpc.SystemPromptBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, system_prompt_builder_service: 'SystemPromptBuilderService') -> None:
        self.system_prompt_builder_service = system_prompt_builder_service


    @GrpcTools.log_grpc_request('Health')  # type: ignore[misc]
    async def Health(
        self,
        request: system_prompt_builder_pb2.HealthRequest,
        context: 'grpc.ServicerContext',
    ) -> system_prompt_builder_pb2.HealthResponse:
        try:
            GrpcTools.validate_proto(request, context)

            health_status: 'HealthStatus' = await self.system_prompt_builder_service.get_health_status()
            response = system_prompt_builder_pb2.HealthResponse(
                status=health_status.status,
                policy_builder_status=health_status.policy_builder_status,
            )

            GrpcTools.validate_proto(response, context)
            return response
        except Exception as ex:  # noqa: BLE001
            logger.error(f'Health check failed: {ex}')
            return system_prompt_builder_pb2.HealthResponse(
                status='unhealthy',
                policy_builder_status='unknown',
            )


    @GrpcTools.log_grpc_request('BuildSystemPrompt')  # type: ignore[misc]
    async def BuildSystemPrompt(
        self,
        request: system_prompt_builder_pb2.BuildSystemPromptRequest,
        context: 'grpc.ServicerContext',
    ) -> system_prompt_builder_pb2.BuildSystemPromptResponse:
        try:
            GrpcTools.validate_proto(request, context)

            result: 'BuildSystemPromptResponse' = await self.system_prompt_builder_service.build_system_prompt()
            if result.success:
                return system_prompt_builder_pb2.BuildSystemPromptResponse(
                    system_prompt=result.system_prompt,
                    success=True,
                )

            return system_prompt_builder_pb2.BuildSystemPromptResponse(
                system_prompt='',
                success=False,
                error=result.error or 'Unknown error',
            )
        except Exception as ex:  # noqa: BLE001
            logger.exception('BuildSystemPrompt failed')
            return system_prompt_builder_pb2.BuildSystemPromptResponse(
                system_prompt='',
                success=False,
                error=str(ex),
            )


