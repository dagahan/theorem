from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import colorama  # type: ignore[import-untyped]
import grpc.aio  # type: ignore[import-untyped]
from loguru import logger

from protobuf_stubs import personality_builder_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.api.personality_builder_api import PersonalityBuilderAPI
from src.services.personality_builder_service import PersonalityBuilderService


class GrpcPersonalityBuilderServer:
    def __init__(self) -> None:
        self.stub = personality_builder_pb2_grpc
        self._server_addr: str = (
            f"{EnvTools.get_service_host('personality_builder')}:{EnvTools.get_service_grpc_port('personality_builder')}"
        )
        self._max_workers: int = 4
        self._options: tuple[tuple[str, int], ...] = (
            ("grpc.keepalive_time_ms", 60_000),
            ("grpc.keepalive_timeout_ms", 20_000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.max_receive_message_length", 64 * 1024 * 1024),
            ("grpc.max_send_message_length", 64 * 1024 * 1024),
        )

        self._grpc_server: grpc.aio.Server | None = None

        service = PersonalityBuilderService()
        self._servicer = PersonalityBuilderAPI(service)

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

        self.stub.add_PersonalityBuilderServiceServicer_to_server(self._servicer, self._grpc_server)
        self._grpc_server.add_insecure_port(self._server_addr)

        await self._grpc_server.start()

        logger.info(
            f"{colorama.Fore.GREEN}gRPC Personality Builder started at "
            f"{colorama.Fore.YELLOW}{self._server_addr}{colorama.Style.RESET_ALL}"
        )

    async def wait_terminated(self) -> None:
        if self._grpc_server is None:
            return
        await self._grpc_server.wait_for_termination()

    async def stop(self, grace: float = 5.0) -> None:
        if self._grpc_server is None:
            return

        logger.info(f"{colorama.Fore.YELLOW}Stopping gRPC Personality Builder{colorama.Style.RESET_ALL}")
        await self._grpc_server.stop(grace=grace)
        self._grpc_server = None
        logger.info(f"{colorama.Fore.GREEN}gRPC Personality Builder stopped{colorama.Style.RESET_ALL}")
