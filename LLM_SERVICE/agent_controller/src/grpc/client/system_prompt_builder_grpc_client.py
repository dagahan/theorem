from __future__ import annotations

import asyncio

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import system_prompt_builder_pb2, system_prompt_builder_pb2_grpc
from src.core.timeouts import TimeoutTools
from src.domain.models import SystemPromptResponse
from src.grpc.grpc_utils import GrpcTools


class SystemPromptBuilderGrpcClient:
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
        self.stub = system_prompt_builder_pb2_grpc.SystemPromptBuilderServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call('system_prompt_builder', 'Health')
    async def health_check(self) -> bool:
        request = system_prompt_builder_pb2.HealthRequest()

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


    @GrpcTools.log_grpc_client_call('system_prompt_builder', 'BuildSystemPrompt')
    async def build_system_prompt(self) -> SystemPromptResponse:
        request = system_prompt_builder_pb2.BuildSystemPromptRequest()

        GrpcTools.validate_proto(request)

        timeout_sec = TimeoutTools.resolve_node_rpc_timeout()

        try:
            if timeout_sec is not None:
                response = await self.stub.BuildSystemPrompt(
                    request,
                    timeout=timeout_sec
                )

            else:
                response = await self.stub.BuildSystemPrompt(request)

        except grpc.aio.AioRpcError as ex:
            status = ex.code()

            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} BuildSystemPrompt deadline exceeded for {self.target}"
                )
                raise asyncio.TimeoutError('system_prompt_builder timeout') from ex

            return SystemPromptResponse(
                system_prompt='',
                success=False,
                error=str(ex)
            )

        except asyncio.CancelledError as ex:
            if timeout_sec is None:
                raise

            message = (
                f"{self.service_name} BuildSystemPrompt timed out after {timeout_sec:.1f}s "
                f"for {self.target}"
            )

            logger.warning(message)

            raise asyncio.TimeoutError(message) from ex

        except grpc.RpcError as ex:
            return SystemPromptResponse(
                system_prompt='',
                success=False,
                error=str(ex)
            )

        if not response.success:
            return SystemPromptResponse(
                system_prompt='',
                success=False,
                error=response.error or 'system_prompt_builder error'
            )

        GrpcTools.validate_proto(response)

        return SystemPromptResponse(
            system_prompt=response.system_prompt,
            success=True
        )
