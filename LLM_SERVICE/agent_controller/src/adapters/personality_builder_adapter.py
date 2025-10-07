from __future__ import annotations

from typing import Any

from loguru import logger

from google.protobuf.message import Message

from src.core.protobuf_converter import ProtobufConverter
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.grpc.client.personality_builder_grpc_client import PersonalityBuilderGrpcClient
from src.pydantic_schemas.agent_controller import PersonalityResponse, Personality


class PersonalityBuilderAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: PersonalityBuilderGrpcClient = registry.register_client(
            'personality_builder', PersonalityBuilderGrpcClient,
        )


    async def build_personalities(
        self,
        persona_names: list[str],
        agent_name: str = "",
    ) -> PersonalityResponse:
        logger.info(f"Starting personality building for personas: {persona_names}, agent: {agent_name}")
        try:
            resp = await self.client.build_personalities(persona_names, agent_name)
            logger.info(f"Personality building completed: {len(resp.personalities)} personalities, success={resp.success}")

            personalities = [self._to_local_personality(p) for p in resp.personalities]

            return PersonalityResponse(
                personalities=personalities,
                success=resp.success,
                error=resp.error,
            )

        except Exception as ex:
            logger.error(f"Personality building failed: {ex}")
            raise


    def _to_local_personality(
        self,
        src: Any
    ) -> Personality:
        if hasattr(src, "HasField"):
            schema_like = src.response_schema if src.HasField("response_schema") else None
        else:
            schema_like = getattr(src, "response_schema", None)

        schema_dict = ProtobufConverter.convert_response_schema(schema_like) if schema_like else None
        
        if schema_dict:
            def _has_proto(x: Any) -> bool:
                if isinstance(x, Message): return True
                if isinstance(x, dict): return any(_has_proto(v) for v in x.values())
                if isinstance(x, list): return any(_has_proto(v) for v in x)
                return False
            
            if _has_proto(schema_dict):
                logger.error(f"Protobuf leaked in schema: {schema_dict}")
                raise TypeError("Protobuf objects found in converted schema")

        return Personality(
            name=getattr(src, "name"),
            system_prompt=getattr(src, "system_prompt"),
            response_schema=schema_dict,
        )


    async def health_check(self) -> bool:
        return await self.client.health_check()


