from __future__ import annotations

import asyncio
import threading
from concurrent import futures
from typing import TYPE_CHECKING, Any

import colorama  # type: ignore
import grpc  # type: ignore
from loguru import logger

from protobuf_stubs import retriever_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.api.retriever_api import RetrieverService


class GRPCServerRunner:
    def __init__(self) -> None:
        self._servicer = RetrieverService()
        self._max_workers = 4
        self._host: str = EnvTools.get_service_host("retriever")
        self._port: int = int(EnvTools.get_service_grpc_port("retriever"))
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

        retriever_pb2_grpc.add_RetrieverServiceServicer_to_server(self._servicer, self._server)
        self._server.add_insecure_port(self._addr)

        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._stopped = threading.Event()


    def _serve_blocking(self) -> None:
        self._server.start()
        self._started.set()

        logger.info(
            f"{colorama.Fore.GREEN}gRPC Retriever started at "
            f"{colorama.Fore.YELLOW}{self._addr}{colorama.Style.RESET_ALL}"
        )

        self._server.wait_for_termination()
        self._stopped.set()


    async def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._serve_blocking,
            name="gRPC-Retriever",
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

        logger.info(f"{colorama.Fore.YELLOW}Stopping gRPC Retriever{colorama.Style.RESET_ALL}")

        fut = self._server.stop(grace=5.0)
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, lambda: fut.wait(timeout=10))
        if self._thread.is_alive():
            self._thread.join(timeout=10)

        logger.info(f"{colorama.Fore.GREEN}gRPC Retriever stopped{colorama.Style.RESET_ALL}")


