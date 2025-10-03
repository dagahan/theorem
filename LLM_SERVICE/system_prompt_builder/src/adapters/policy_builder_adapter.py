from __future__ import annotations

from typing import TYPE_CHECKING
from loguru import logger
from src.grpc.client.policy_builder_grpc_client import PolicyBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.pydantic_schemas.system_prompt_builder import PolicyHeaderResponse


class PolicyBuilderAdapter:
    def __init__(self) -> None:
        self.policy_builder_client: PolicyBuilderGrpcClient = GrpcClientRegistry().register_client("policy_builder", PolicyBuilderGrpcClient)


    async def get_policy_header(self) -> PolicyHeaderResponse:
        return await self.policy_builder_client.get_policy_header()


    async def health_check(self) -> bool:
        response = await self.policy_builder_client.health_check()
        return bool(response.success and response.status == "healthy")
            

