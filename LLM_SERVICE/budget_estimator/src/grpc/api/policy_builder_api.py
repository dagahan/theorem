from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from loguru import logger
from protobuf_stubs import policy_builder_pb2, policy_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools


if TYPE_CHECKING:
    from src.pydantic_schemas.budget_estimator import HealthStatus, PolicyResponse
    from src.services.policy_builder_service import PolicyBuilderService


class PolicyBuilderAPI(policy_builder_pb2_grpc.PolicyBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self, policy_builder_service: 'PolicyBuilderService') -> None:
        self.policy_builder_service = policy_builder_service


    @GrpcTools.log_grpc_request('Health')  # type: ignore[misc]
    async def Health(
        self,
        request: policy_builder_pb2.HealthRequest,
        context: Any,
    ) -> policy_builder_pb2.HealthResponse:
        try:
            GrpcTools.validate_proto(request, context)

            result: 'HealthStatus' = await asyncio.to_thread(self.policy_builder_service.get_health_status)
            response = policy_builder_pb2.HealthResponse(status=result.status)

            GrpcTools.validate_proto(response, context)
            return response
        except Exception as ex:  # noqa: BLE001
            logger.error(f'Health check failed: {ex}')
            return policy_builder_pb2.HealthResponse(status='unhealthy')


    @GrpcTools.log_grpc_request('BuildPolicy')  # type: ignore[misc]
    async def BuildPolicy(
        self,
        request: policy_builder_pb2.BuildPolicyRequest,
        context: Any,
    ) -> policy_builder_pb2.BuildPolicyResponse:
        GrpcTools.validate_proto(request, context)

        try:
            policy_result: 'PolicyResponse' = await asyncio.to_thread(
                self.policy_builder_service.build_policy
            )

            if policy_result.success:
                response = policy_builder_pb2.BuildPolicyResponse(
                    policy_header=policy_result.policy_header,
                    success=True,
                )
            else:
                response = policy_builder_pb2.BuildPolicyResponse(
                    policy_header='',
                    success=False,
                    error=policy_result.error or 'Unknown error',
                )

            GrpcTools.validate_proto(response, context)
            return response
        except Exception as ex:  # noqa: BLE001
            logger.exception('BuildPolicy failed')
            return policy_builder_pb2.BuildPolicyResponse(
                success=False,
                error=str(ex),
            )


