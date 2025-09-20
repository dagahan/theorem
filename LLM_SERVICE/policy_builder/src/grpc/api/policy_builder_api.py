from __future__ import annotations

from typing import TYPE_CHECKING, Any
from protobuf_stubs import policy_builder_pb2, policy_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools

if TYPE_CHECKING:
    from src.domain.models import PolicyResponse, HealthStatus
    from src.services.policy_builder_service import PolicyBuilderService


grpc_tools = GrpcTools()


class PolicyBuilderAPI(policy_builder_pb2_grpc.PolicyBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, policy_builder_service: "PolicyBuilderService") -> None:
        self.policy_builder_service = policy_builder_service


    @grpc_tools.log_grpc_request("Health")  # type: ignore[misc]
    def Health(self, request: policy_builder_pb2.HealthRequest, context: Any) -> policy_builder_pb2.HealthResponse:

        grpc_tools.validate_proto(request, context)

        result: HealthStatus = self.policy_builder_service.get_health_status()

        response = policy_builder_pb2.HealthResponse(
            status=result.status
        )

        grpc_tools.validate_proto(response, context)

        return response


    @grpc_tools.log_grpc_request("BuildPolicy")  # type: ignore[misc]
    def BuildPolicy(self, request: policy_builder_pb2.BuildPolicyRequest, context: Any) -> policy_builder_pb2.BuildPolicyResponse:

        grpc_tools.validate_proto(request, context)

        try:
            policy_result: PolicyResponse = self.policy_builder_service.build_policy()

            if policy_result.success:
                response = policy_builder_pb2.BuildPolicyResponse(
                    policy_header=policy_result.policy_header,
                    success=True
                )

            else:
                response = policy_builder_pb2.BuildPolicyResponse(
                    policy_header="",
                    success=False,
                    error=policy_result.error or "Unknown error"
                )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:
            return policy_builder_pb2.BuildPolicyResponse(
                success=False,
                error=str(ex)
            )


