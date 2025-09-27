from __future__ import annotations

import asyncio
import signal
import sys

import colorama
from loguru import logger

from src.core.logging import InterceptHandler, LogSetup
from src.core.utils import EnvTools
from src.grpc.grpc_server import GrpcAgentControllerServer


class Service:
    def __init__(self) -> None:
        self.interceptor = InterceptHandler()
        self.logger_setup = LogSetup()
        self.grpc_server = GrpcAgentControllerServer()

    async def run_service(self) -> None:
        self.logger_setup.configure()

        loop = asyncio.get_running_loop()
        stop_future: asyncio.Future[None] = loop.create_future()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: (not stop_future.done()) and stop_future.set_result(None))

        await self.grpc_server.start()

        waiter = asyncio.create_task(self.grpc_server.wait_terminated(), name="gRPC-Agent-Controller")
        pending = {waiter, stop_future}

        try:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task is stop_future:
                    logger.info(f"{colorama.Fore.YELLOW}Shutdown signal received{colorama.Style.RESET_ALL}")
                elif isinstance(task, asyncio.Task) and task.exception():
                    logger.error(f"{colorama.Fore.RED}{task.get_name()} crashed: {task.exception()}{colorama.Style.RESET_ALL}")

        finally:
            await self.grpc_server.stop()

            for task in pending:
                if isinstance(task, asyncio.Task):
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            logger.info(f"{colorama.Fore.GREEN}All servers stopped gracefully{colorama.Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        EnvTools.bootstrap_env(service_name="agent_controller", conf_filename=".conf")
        asyncio.run(Service().run_service())

    except KeyboardInterrupt:
        logger.info(f"{colorama.Fore.CYAN}Service stopped by user{colorama.Style.RESET_ALL}")

    except Exception as ex:
        logger.critical(f"{colorama.Fore.RED}Service crashed: {ex}{colorama.Style.RESET_ALL}")
        sys.exit(1)
