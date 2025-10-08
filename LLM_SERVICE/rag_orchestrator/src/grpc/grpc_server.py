from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import colorama  # type: ignore
import grpc.aio  # type: ignore
from loguru import logger

from protobuf_stubs import rag_orchestrator_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.api.rag_orchestrator_api import RagOrchestratorService


class GrpcRagOrchestratorServer:
    def __init__(self) -> None:
        self.stub = rag_orchestrator_pb2_grpc
        self._server_addr: str = (
            f"{EnvTools.get_service_host('rag_orchestrator')}:{EnvTools.get_service_grpc_port('rag_orchestrator')}"
        )

        max_workers_env = EnvTools.load_env_var("RAG_ORCHESTRATOR_MAX_CONCURRENCY")
        self._max_workers: int = int(max_workers_env) if max_workers_env else 16
        self._options: tuple[tuple[str, int], ...] = (
            ("grpc.keepalive_time_ms", 60_000),
            ("grpc.keepalive_timeout_ms", 20_000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
        )

        self._grpc_server: grpc.aio.Server | None = None
        self._servicer: RagOrchestratorService | None = None


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
            self._servicer = RagOrchestratorService()

        self.stub.add_RagOrchestratorServiceServicer_to_server(self._servicer, self._grpc_server)
        self._grpc_server.add_insecure_port(self._server_addr)

        await self._grpc_server.start()

        logger.info(
            f"{colorama.Fore.GREEN}RAG Orchestrator gRPC server started on {self._server_addr}{colorama.Style.RESET_ALL}"
        )


    async def stop(self) -> None:
        if self._grpc_server is None:
            return

        logger.info(
            f"{colorama.Fore.YELLOW}Stopping RAG Orchestrator gRPC server...{colorama.Style.RESET_ALL}"
        )

        await self._grpc_server.stop(grace=5.0)
        self._grpc_server = None

        logger.info(
            f"{colorama.Fore.GREEN}RAG Orchestrator gRPC server stopped{colorama.Style.RESET_ALL}"
        )


    async def wait_terminated(self) -> None:
        if self._grpc_server is None:
            return

        await self._grpc_server.wait_for_termination()


        