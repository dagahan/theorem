from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import colorama
import grpc.aio
from loguru import logger

from protobuf_stubs import agent_controller_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.api.agent_controller_api import AgentControllerAPI
from src.services.orchestrator import LLMGraphOrchestrator


class GrpcAgentControllerServer:
    def __init__(self) -> None:
        self.stub = agent_controller_pb2_grpc
        self._server_addr: str = f"{EnvTools.get_service_host('agent_controller')}:{EnvTools.get_service_grpc_port('agent_controller')}"
        self._max_workers: int = int(EnvTools.required_load_env_var("AGENT_CONTROLLER_MAX_CONCURRENCY"))
        self._options: tuple[tuple[str, int], ...] = (
            ("grpc.keepalive_time_ms", 60_000),
            ("grpc.keepalive_timeout_ms", 20_000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
        )

        self._grpc_server: grpc.aio.Server | None = None
        self._servicer: AgentControllerAPI | None = None


    @property
    def is_running(self) -> bool:
        return self._grpc_server is not None


    async def start(self) -> None:
        if self._grpc_server is not None:
            return

        self._grpc_server = grpc.aio.server(
            ThreadPoolExecutor(max_workers=self._max_workers),
            options=self._options,
        )

        if self._servicer is None:
            orchestrator = LLMGraphOrchestrator()
            self._servicer = AgentControllerAPI(orchestrator)

        self.stub.add_AgentControllerServiceServicer_to_server(
            self._servicer,
            self._grpc_server,
        )

        self._grpc_server.add_insecure_port(self._server_addr)
        await self._grpc_server.start()

        logger.info(
            f"{colorama.Fore.GREEN}gRPC Agent Controller started at "
            f"{colorama.Fore.YELLOW}{self._server_addr}{colorama.Style.RESET_ALL}"
        )


    async def wait_terminated(self) -> None:
        if self._grpc_server is None:
            return
        await self._grpc_server.wait_for_termination()


    async def stop(
        self,
        grace: float = 5.0,
    ) -> None:
        if self._grpc_server is None:
            return

        logger.info(f"{colorama.Fore.YELLOW}Stopping gRPC Agent Controller{colorama.Style.RESET_ALL}")
        await self._grpc_server.stop(grace=grace)
        self._grpc_server = None
        logger.info(f"{colorama.Fore.GREEN}gRPC Agent Controller stopped{colorama.Style.RESET_ALL}")


