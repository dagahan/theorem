from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import colorama
import grpc.aio
from loguru import logger

from protobuf_stubs import embedder_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.api.embedder_api import EmbedderAPI
from src.services.embedder_service import EmbedderService


class GrpcEmbedderServer:
    def __init__(self) -> None:
        self.stub = embedder_pb2_grpc
        self._server_addr: str = f"{EnvTools.get_service_host('embedder')}:{EnvTools.get_service_grpc_port('embedder')}"
        max_workers_env = EnvTools.load_env_var("EMBEDDER_MAX_CONCURRENCY")
        self._max_workers: int = int(max_workers_env) if max_workers_env else 4
        self._options: tuple[tuple[str, int], ...] = (
            ("grpc.keepalive_time_ms", 60_000),
            ("grpc.keepalive_timeout_ms", 20_000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
        )

        self._grpc_server: grpc.aio.Server | None = None

        service = EmbedderService()
        self._servicer = EmbedderAPI(service)

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

        self.stub.add_EmbedderServiceServicer_to_server(self._servicer, self._grpc_server)
        self._grpc_server.add_insecure_port(self._server_addr)

        await self._grpc_server.start()

        logger.info(
            f"{colorama.Fore.GREEN}gRPC embedder started at "
            f"{colorama.Fore.YELLOW}{self._server_addr}{colorama.Style.RESET_ALL}"
        )

    async def wait_terminated(self) -> None:
        if self._grpc_server is None:
            return
        await self._grpc_server.wait_for_termination()

    async def stop(self, grace: float = 5.0) -> None:
        if self._grpc_server is None:
            return

        logger.info(f"{colorama.Fore.YELLOW}Stopping gRPC embedder{colorama.Style.RESET_ALL}")
        await self._grpc_server.stop(grace=grace)
        self._grpc_server = None
        logger.info(f"{colorama.Fore.GREEN}gRPC embedder stopped{colorama.Style.RESET_ALL}")
