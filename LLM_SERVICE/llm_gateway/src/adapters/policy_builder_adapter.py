from __future__ import annotations
import grpc
from loguru import logger
from src.core.utils import EnvTools
from src.domain.models import PolicyRequest, PolicyResponse, PolicyHeader
from protobuf_stubs import policy_builder_pb2, policy_builder_pb2_grpc


class PolicyBuilderAdapter:
    def __init__(self) -> None:
        self.host = EnvTools.get_service_host("policy_builder")
        self.port = EnvTools.get_service_grpc_port("policy_builder")
        self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
        self.client = policy_builder_pb2_grpc.PolicyBuilderServiceStub(self.channel)


    async def build_policy(
        self,
        request: PolicyRequest
    ) -> PolicyResponse:
        try:
            grpc_request = policy_builder_pb2.BuildPolicyRequest()
            
            grpc_response = self.client.BuildPolicy(grpc_request, timeout=10.0)
            
            if not grpc_response.success:
                error_msg = f"Policy builder service returned error: {grpc_response.error}"
                logger.error(error_msg)
                return PolicyResponse(
                    policy_header=self._get_default_policy(),
                    success=False,
                    error=error_msg
                )
            
            policy_header = PolicyHeader(
                policy_header=grpc_response.policy_header
            )
            
            return PolicyResponse(
                policy_header=policy_header.policy_header,
                success=True
            )
            
        except Exception as ex:
            logger.error(f"Policy builder adapter failed: {ex}")
            return PolicyResponse(
                policy_header=self._get_default_policy(),
                success=False,
                error=str(ex)
            )


    def _get_default_policy(self) -> str:
        return "Answer only with lawful, non-harmful, non-sexual, non-violent, and non-hate content; decline and do not facilitate wrongdoing or unsafe acts."


    async def health_check(self) -> bool:
        try:
            grpc_request = policy_builder_pb2.HealthRequest()
            grpc_response = self.client.Health(grpc_request, timeout=5.0)
            return bool(grpc_response.status == "healthy")

        except Exception:
            return False