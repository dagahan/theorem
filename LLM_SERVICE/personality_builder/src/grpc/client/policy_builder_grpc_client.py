from __future__ import annotations

import grpc
from loguru import logger

from protobuf_stubs import policy_builder_pb2, policy_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.pydantic_schemas.personality_builder import PolicyHeaderResponse, PolicyHealthResponse


class PolicyBuilderGrpcClient:
    def __init__(self, channel: grpc.Channel, service_name: str) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.stub = policy_builder_pb2_grpc.PolicyBuilderServiceStub(self.channel)


    async def health_check(self) -> PolicyHealthResponse:
        request = policy_builder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)
        
        try:
            response = self.stub.Health(request, timeout=3)
            GrpcTools.validate_proto(response)

            return PolicyHealthResponse(
                status=response.status,
                success=True
            )

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            return PolicyHealthResponse(
                status="unhealthy",
                success=False,
                error=str(ex)
            )


    async def get_policy_header(self) -> PolicyHeaderResponse:
        request = policy_builder_pb2.BuildPolicyRequest()
        GrpcTools.validate_proto(request)
        
        try:
            response = self.stub.BuildPolicy(request)
            
            if not response.success:
                return PolicyHeaderResponse(
                    policy_header="",
                    success=False,
                    error=response.error or "policy_builder error"
                )
            
            GrpcTools.validate_proto(response)

            return PolicyHeaderResponse(
                policy_header=response.policy_header,
                success=True
            )

        except grpc.RpcError as ex:
            logger.error(f"Get policy header failed: {ex}")
            return PolicyHeaderResponse(
                policy_header="",
                success=False,
                error=str(ex)
            )


