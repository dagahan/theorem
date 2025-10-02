from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from protobuf_stubs import system_prompt_builder_pb2, system_prompt_builder_pb2_grpc
from src.domain.models import BuildSystemPromptRequest, BuildSystemPromptResponse
from src.grpc.grpc_utils import GrpcTools

if TYPE_CHECKING:
    import grpc
    from src.services.system_prompt_builder_service import SystemPromptBuilderService


grpc_tools = GrpcTools()


class SystemPromptBuilderAPI(system_prompt_builder_pb2_grpc.SystemPromptBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, system_prompt_builder_service: SystemPromptBuilderService) -> None:
        self.system_prompt_builder_service = system_prompt_builder_service


    @grpc_tools.log_grpc_request('Health')  # type: ignore[misc]
    async def Health(
        self,
        request: system_prompt_builder_pb2.HealthRequest,
        context: 'grpc.ServicerContext',
    ) -> system_prompt_builder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_status = await self.system_prompt_builder_service.get_health_status()

            response = system_prompt_builder_pb2.HealthResponse(
                status=health_status.status,
                policy_builder_status=health_status.policy_builder_status,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as exc:  # noqa: BLE001
            logger.error('Health check failed: %s', exc)
            return system_prompt_builder_pb2.HealthResponse(
                status='unhealthy',
                policy_builder_status='unknown',
            )


    @grpc_tools.log_grpc_request('BuildSystemPrompt')  # type: ignore[misc]
    async def BuildSystemPrompt(
        self,
        request: system_prompt_builder_pb2.BuildSystemPromptRequest,
        context: 'grpc.ServicerContext',
    ) -> system_prompt_builder_pb2.BuildSystemPromptResponse:
        try:
            grpc_tools.validate_proto(request, context)

            persona_names = list(request.persona_names) or ['Responder']

            request_model = BuildSystemPromptRequest(persona_names=persona_names)

            result = await self.system_prompt_builder_service.build_persona_system_prompt(request_model)

            if not result.success:
                return system_prompt_builder_pb2.BuildSystemPromptResponse(
                    personalities=[],
                    success=False,
                    error=result.error or 'system_prompt_builder error',
                )

            response = system_prompt_builder_pb2.BuildSystemPromptResponse(
                personalities=[
                    system_prompt_builder_pb2.PersonaPrompt(name=item.name, prompt=item.prompt)
                    for item in result.personalities
                ],
                success=True,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as exc:  # noqa: BLE001
            logger.exception('BuildSystemPrompt failed')
            return system_prompt_builder_pb2.BuildSystemPromptResponse(
                personalities=[],
                success=False,
                error=str(exc),
            )

