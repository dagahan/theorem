from __future__ import annotations

from typing import TYPE_CHECKING

from google.protobuf import struct_pb2
from loguru import logger

from protobuf_stubs import personality_builder_pb2, personality_builder_pb2_grpc
from src.pydantic_schemas.personality_builder import BuildPersonalityRequest, BuildPersonalityResponse
from src.grpc.grpc_utils import GrpcTools

if TYPE_CHECKING:
    import grpc
    from src.services.personality_builder_service import PersonalityBuilderService


grpc_tools = GrpcTools()


class PersonalityBuilderAPI(personality_builder_pb2_grpc.PersonalityBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, personality_builder_service: 'PersonalityBuilderService') -> None:
        self.personality_builder_service = personality_builder_service


    @grpc_tools.log_grpc_request('Health')  # type: ignore[misc]
    async def Health(
        self,
        request: personality_builder_pb2.HealthRequest,
        context: 'grpc.ServicerContext',
    ) -> personality_builder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            health_status = await self.personality_builder_service.get_health_status()

            response = personality_builder_pb2.HealthResponse(
                status=health_status.status,
                policy_builder_status=health_status.policy_builder_status,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as exc:  # noqa: BLE001
            logger.error('Health check failed: %s', exc)
            return personality_builder_pb2.HealthResponse(
                status='unhealthy',
                policy_builder_status='unknown',
            )


    @grpc_tools.log_grpc_request('BuildPersonality')  # type: ignore[misc]
    async def BuildPersonality(
        self,
        request: personality_builder_pb2.BuildPersonalityRequest,
        context: 'grpc.ServicerContext',
    ) -> personality_builder_pb2.BuildPersonalityResponse:
        try:
            grpc_tools.validate_proto(request, context)

            persona_names = list(request.persona_names) or ['Responder']
            agent_name = request.agent_name or ""

            request_model = BuildPersonalityRequest(persona_names=persona_names, agent_name=agent_name)

            result = await self.personality_builder_service.build_personalities(request_model, agent_name)

            if not result.success:
                return personality_builder_pb2.BuildPersonalityResponse(
                    personalities=[],
                    success=False,
                    error=result.error or 'personality_builder error',
                )

            personalities = []
            for item in result.personalities:
                response_schema = None
                if item.response_schema:
                    properties_struct = struct_pb2.Struct()
                    properties_dict = item.response_schema.properties if isinstance(item.response_schema.properties, dict) else {}
                    properties_struct.update(properties_dict)
                    
                    response_schema = personality_builder_pb2.ResponseSchema(
                        type=item.response_schema.type,
                        properties=properties_struct,
                        required=item.response_schema.required,
                        title=item.response_schema.title or "",
                        description=item.response_schema.description or ""
                    )
                
                personalities.append(personality_builder_pb2.Personality(
                    name=item.name, 
                    system_prompt=item.system_prompt,
                    response_schema=response_schema
                ))

            response = personality_builder_pb2.BuildPersonalityResponse(
                personalities=personalities,
                success=True,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as exc:  # noqa: BLE001
            logger.exception('BuildPersonality failed')
            return personality_builder_pb2.BuildPersonalityResponse(
                personalities=[],
                success=False,
                error=str(exc),
            )

