from __future__ import annotations

import asyncio

import grpc
import grpc.aio
from loguru import logger

from protobuf_stubs import personality_builder_pb2, personality_builder_pb2_grpc
from src.core.timeouts import TimeoutTools
from src.pydantic_schemas.agent_controller import PersonalityResponse
from src.pydantic_schemas.personality_builder import Personality, ResponseSchema
from src.grpc.grpc_utils import GrpcTools


class PersonalityBuilderGrpcClient:
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
        self.stub = personality_builder_pb2_grpc.PersonalityBuilderServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call('personality_builder', 'Health')
    async def health_check(self) -> bool:
        request = personality_builder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)

        timeout_sec = TimeoutTools.get_health_check_timeout()

        try:
            response = await self.stub.Health(
                request,
                timeout=timeout_sec
            )

            GrpcTools.validate_proto(response)

            return response.status == 'healthy'  # type: ignore

        except grpc.RpcError:
            return False


    @GrpcTools.log_grpc_client_call('personality_builder', 'BuildPersonality')
    async def build_personalities(
        self,
        persona_names: list[str],
        agent_name: str = "",
    ) -> PersonalityResponse:
        request = personality_builder_pb2.BuildPersonalityRequest(
            persona_names=persona_names,
            agent_name=agent_name
        )

        GrpcTools.validate_proto(request)

        timeout_sec = TimeoutTools.resolve_node_rpc_timeout()

        try:
            if timeout_sec is not None:
                response = await self.stub.BuildPersonality(
                    request,
                    timeout=timeout_sec
                )

            else:
                response = await self.stub.BuildPersonality(request)

        except grpc.aio.AioRpcError as ex:
            status = ex.code()
            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} BuildPersonality deadline exceeded for {self.target}"
                )

                raise asyncio.TimeoutError('personality_builder timeout') from ex

            return PersonalityResponse(
                personalities={},
                success=False,
                error=str(ex)
            )

        except asyncio.CancelledError as ex:
            if timeout_sec is None:
                raise

            message = (
                f"{self.service_name} BuildPersonality timed out after {timeout_sec:.1f}s "
                f"for {self.target}"
            )

            logger.warning(message)
            raise asyncio.TimeoutError(message) from ex

        except grpc.RpcError as ex:
            return PersonalityResponse(
                personalities={},
                success=False,
                error=str(ex)
            )

        GrpcTools.validate_proto(response)

        if not response.success:
            return PersonalityResponse(
                personalities={},
                success=False,
                error=response.error or 'personality_builder error'
            )

        # Convert proto response to Pydantic models

        personalities = []
        
        for item in response.personalities:
            response_schema = None

            if item.response_schema:
                response_schema = ResponseSchema(
                    type=item.response_schema.type,
                    properties=dict(item.response_schema.properties),
                    required=list(item.response_schema.required),
                    title=item.response_schema.title or None,
                )
            
            personality = Personality(
                name=item.name,
                system_prompt=item.system_prompt,
                response_schema=response_schema
            )

            personalities.append(personality)

        return PersonalityResponse(
            personalities=personalities,
            success=True
        )

        