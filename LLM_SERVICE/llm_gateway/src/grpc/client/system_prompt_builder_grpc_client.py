from __future__ import annotations

import grpc.aio
from loguru import logger

from protobuf_stubs import system_prompt_builder_pb2, system_prompt_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.domain.models import SystemPromptResponse


class SystemPromptBuilderGrpcClient:
    def __init__(self, channel: grpc.aio.Channel, service_name: str) -> None:
        self.channel = channel
        self.service_name = service_name
        self.stub = system_prompt_builder_pb2_grpc.SystemPromptBuilderServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call("system_prompt_builder", "Health")
    async def health_check(self) -> bool:
        request = system_prompt_builder_pb2.HealthRequest()

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.Health(request, timeout=3)
            GrpcTools.validate_proto(response)
            return bool(response.status == "healthy")

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            return False


    @GrpcTools.log_grpc_client_call("system_prompt_builder", "BuildSystemPrompt")
    async def build_system_prompt(self) -> SystemPromptResponse:
        request = system_prompt_builder_pb2.BuildSystemPromptRequest()

        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.BuildSystemPrompt(request, timeout=30)

            if not response.success:
                return SystemPromptResponse(
                    system_prompt="",
                    success=False,
                    error=response.error or "system_prompt error"
                )

            GrpcTools.validate_proto(response)

            return SystemPromptResponse(
                system_prompt=response.system_prompt,
                success=True
            )

        except grpc.RpcError as ex:
            logger.error(f"BuildSystemPrompt failed: {ex}")
            return SystemPromptResponse(system_prompt="", success=False, error=str(ex))
