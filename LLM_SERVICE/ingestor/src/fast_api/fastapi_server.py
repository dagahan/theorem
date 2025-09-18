import uvicorn
from fastapi import FastAPI
from loguru import logger

from src.core.utils import EnvTools
from src.db.database_connector import DataBaseConnector
from src.fast_api.routers.health_router import get_health_router
from src.fast_api.routers.vector_store_router import get_vector_store_router
from src.fast_api.routers.statistics_router import get_statistics_router
from src.fast_api.routers.ingestor_router import get_ingestor_router


class Server:
    def __init__(self) -> None:
        self.app = FastAPI(
            title="ingestor",
            description="insert data to qdrant service.",
            version="0.0.1"
        )

        self.database_connector = DataBaseConnector()

        self.uvicorn_config = uvicorn.Config(
            app=self.app,
            host = EnvTools.get_service_host("ingestor"),
            port = int(EnvTools.get_service_http_port("ingestor")),
            log_level="info"
        )

        self.server: uvicorn.Server | None = None

    
    async def run_server(self) -> None:
        """
        Starting uvicorn web server, register routes
        and initialize database connector.
        """
        server = uvicorn.Server(self.uvicorn_config)
        await self.database_connector.init_alchemy_engine()
        # await self.database_connector.drop_all_tables()
        await self.database_connector.create_tables()
        await self._register_routes()

        logger.info(f"Starting {self.app.title} Fast API server.")
        
        await server.serve()


    async def stop(self) -> None:
        """
        gracefully stop uvicorn server from outside.
        """
        if not self.server:
            return

        self.server.should_exit = True

        shutdown = getattr(self.server, "shutdown", None)
        if callable(shutdown):
            try:
                await shutdown() 
            except Exception as ex:
                logger.debug(f"uvicorn shutdown() raised: {ex}")


    async def _register_routes(self) -> None:
        '''
        register all of endpoints.
        '''
        self.app.include_router(get_health_router())
        self.app.include_router(get_vector_store_router(self.database_connector))
        self.app.include_router(get_statistics_router(self.database_connector))
        self.app.include_router(get_ingestor_router(self.database_connector))
            

