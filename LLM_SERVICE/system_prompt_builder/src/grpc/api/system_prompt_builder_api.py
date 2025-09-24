from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import grpc
    from src.services.policy_builder_service import SystemPromptBuilderService
    from src.domain.models import (
        HealthStatus, BuildSystemPromptResponse
    )

from protobuf_stubs import system_prompt_builder_pb2, system_prompt_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools

grpc_tools = GrpcTools()


class SystemPromptBuilderAPI(system_prompt_builder_pb2_grpc.SystemPromptBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, system_prompt_builder_service: "SystemPromptBuilderService") -> None:
        self.system_prompt_builder_service = system_prompt_builder_service


    @grpc_tools.log_grpc_request("Health")  # type: ignore[misc]
    def Health(self, request: system_prompt_builder_pb2.HealthRequest, context: "grpc.ServicerContext") -> system_prompt_builder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_status: "HealthStatus" = asyncio.run(self.system_prompt_builder_service.get_health_status())

            response = system_prompt_builder_pb2.HealthResponse(
                status=health_status.status,
                policy_builder_status=health_status.policy_builder_status,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:
            return system_prompt_builder_pb2.HealthResponse(
                status="unhealthy",
                policy_builder_status="unknown"
            )


    @grpc_tools.log_grpc_request("BuildSystemPrompt")  # type: ignore[misc]
    def BuildSystemPrompt(self, request: system_prompt_builder_pb2.BuildSystemPromptRequest, context: "grpc.ServicerContext") -> system_prompt_builder_pb2.BuildSystemPromptResponse:
        try:
            grpc_tools.validate_proto(request, context)

            result: "BuildSystemPromptResponse" = asyncio.run(self.system_prompt_builder_service.build_system_prompt())

            if result.success:
                return system_prompt_builder_pb2.BuildSystemPromptResponse(
                    system_prompt=result.system_prompt,
                    success=True
                )

            else:
                return system_prompt_builder_pb2.BuildSystemPromptResponse(
                    system_prompt="",
                    success=False,
                    error=result.error or "Unknown error"
                )

        except Exception as ex:
            return system_prompt_builder_pb2.BuildSystemPromptResponse(
                system_prompt="",
                success=False,
                error=str(ex)
            )


            