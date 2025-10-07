import asyncio
import signal
import sys

import colorama
from loguru import logger

from src.core.logging import InterceptHandler, LogSetup
from src.core.utils import EnvTools
from src.mcp.mcp_server import McpServer


class Service:
    def __init__(self) -> None:
        self.intercept_handler = InterceptHandler()
        self.logger_setup = LogSetup()
        self.mcp_server = McpServer()


    async def run_service(self) -> None:
        self.logger_setup.configure()

        loop = asyncio.get_running_loop()
        stop_future: asyncio.Future[None] = loop.create_future()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: (not stop_future.done()) and stop_future.set_result(None))
        
        await self.mcp_server.start()

        waiter = asyncio.create_task(self.mcp_server.wait_terminated(), name="MCP-Server")
        pending = {waiter, stop_future}

        try:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                if task is stop_future:
                    logger.info(f"{colorama.Fore.YELLOW}Shutdown signal received{colorama.Style.RESET_ALL}")
                elif isinstance(task, asyncio.Task) and task.exception():
                    logger.error(f"{colorama.Fore.RED}{task.get_name()} crashed: {task.exception()}{colorama.Style.RESET_ALL}")

        finally:
            await self.mcp_server.stop()

            for task in pending:
                if isinstance(task, asyncio.Task):
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            logger.info(f"{colorama.Fore.GREEN}All servers stopped gracefully{colorama.Style.RESET_ALL}")


if __name__ == "__main__":
    # loading env variables process for local run of microservice.
    try:
        EnvTools.bootstrap_env(
            service_name="mcp_server",
            conf_filename=".conf"
        )

    except Exception as ex:
        raise Exception(f"bootstrap_env failed: {ex}")

    try:
        asyncio.run(Service().run_service())
    except KeyboardInterrupt:
        logger.info(
            f"{colorama.Fore.CYAN}Service stopped by user{colorama.Style.RESET_ALL}"
        )
    except Exception as e:
        logger.critical(
            f"{colorama.Fore.RED}Service crashed: {e}{colorama.Style.RESET_ALL}"
        )

        sys.exit(1)

