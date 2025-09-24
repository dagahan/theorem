from __future__ import annotations

import asyncio
import threading
from concurrent import futures
from typing import TYPE_CHECKING, Any

import colorama
import grpc
from loguru import logger

from protobuf_stubs import embedder_pb2_grpc
from src.core.utils import EnvTools
from src.services.embedder_service import EmbedderService
from src.grpc.api.embedder_api import EmbedderAPI


class GRPCServerRunner:
    def __init__(self) -> None:
        self._embedder_service = EmbedderService()
        self._servicer = EmbedderAPI(self._embedder_service)
        self._max_workers = int(EnvTools.required_load_env_var("EMBEDDER_MAX_CONCURRENCY"))
        self._host: str = EnvTools.get_service_host("embedder")
        self._port: int = int(EnvTools.get_service_grpc_port("embedder"))
        self._addr = f"{self._host}:{self._port}"

        self._GRPC_OPTIONS = (
            ("grpc.keepalive_time_ms", 60_000),
            ("grpc.keepalive_timeout_ms", 20_000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
        )

        self._server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self._max_workers),
            options=self._GRPC_OPTIONS,
        )

        embedder_pb2_grpc.add_EmbedderServiceServicer_to_server(self._servicer, self._server)
        self._server.add_insecure_port(self._addr)

        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._stopped = threading.Event()


    def _serve_blocking(self) -> None:
        self._server.start()
        self._started.set()

        logger.info(
            f"{colorama.Fore.GREEN}gRPC embedder started at "
            f"{colorama.Fore.YELLOW}{self._addr}{colorama.Style.RESET_ALL}"
        )

        self._server.wait_for_termination()
        self._stopped.set()


    async def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._serve_blocking,
            name="gRPC-Embedder",
            daemon=True)
        self._thread.start()
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, self._started.wait)


    async def wait_terminated(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._stopped.wait)


    async def stop(self) -> None:
        if not self._thread:
            return

        logger.info(f"{colorama.Fore.YELLOW}Stopping gRPC embedder{colorama.Style.RESET_ALL}")

        fut = self._server.stop(grace=5.0)
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, lambda: fut.wait(timeout=10))
        if self._thread.is_alive():
            self._thread.join(timeout=10)

        logger.info(f"{colorama.Fore.GREEN}gRPC embedder stopped{colorama.Style.RESET_ALL}")


