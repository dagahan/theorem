from __future__ import annotations

import asyncio

import grpc  # type: ignore[import-untyped]
import grpc.aio  # type: ignore[import-untyped]
from loguru import logger

from protobuf_stubs import agent_controller_pb2, agent_controller_pb2_grpc
from src.grpc.grpc_utils import GrpcTools


class AgentControllerGrpcClient:
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
        self.stub = agent_controller_pb2_grpc.AgentControllerServiceStub(self.channel)


    @GrpcTools.log_grpc_client_call('agent_controller', 'Health')
    async def health_check(self) -> agent_controller_pb2.HealthResponse:
        request = agent_controller_pb2.HealthRequest()
        GrpcTools.validate_proto(request)

        response = await self.stub.Health(request, timeout=5)
        GrpcTools.validate_proto(response)
        return response


    @GrpcTools.log_grpc_client_call('agent_controller', 'AnswerQuestion')
    async def answer_question(
        self,
        raw_text: str,
        stream: bool,
        agent_name: str,
        run_id: str | None = None,
    ) -> agent_controller_pb2.QuestionResponse:
        request = agent_controller_pb2.QuestionRequest(
            raw_text=raw_text,
            stream=stream,
            run_id=run_id or '',
            agent_name=agent_name,
        )
        GrpcTools.validate_proto(request)

        try:
            response = await self.stub.AnswerQuestion(request, timeout=120)
        except grpc.aio.AioRpcError as exc:
            status = exc.code()
            if status in (grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.CANCELLED):
                logger.warning(
                    f"{self.service_name} AnswerQuestion deadline exceeded for {self.target}"
                )
                raise asyncio.TimeoutError('agent_controller timeout') from exc
            logger.error(
                f"{self.service_name} AnswerQuestion failed for {self.target}: {exc}"
            )
            raise

        GrpcTools.validate_proto(response)
        return response

