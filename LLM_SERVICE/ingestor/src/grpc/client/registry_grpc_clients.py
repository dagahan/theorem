import grpc  # type: ignore
from loguru import logger

from src.core.utils import EnvTools
from .embedder_grpc_client import EmbedderGrpcClient


class RegistryGrpcClients:
    def __init__(self) -> None:
        self.embedder_client: EmbedderGrpcClient | None = None
        self._init_grpc_clients()


    def _init_grpc_clients(self) -> None:
        try:
            embedder_host = EnvTools.get_service_ip("embedder")
            embedder_port = EnvTools.get_service_port("embedder")
            
            embedder_channel = grpc.aio.insecure_channel(f"{embedder_host}:{embedder_port}")
            self.embedder_client = EmbedderGrpcClient(embedder_channel)
            
            logger.info(f"gRPC clients initialized. Embedder: {embedder_host}:{embedder_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize gRPC clients: {e}")
            raise


    async def get_embedder_client(self) -> EmbedderGrpcClient:
        if not self.embedder_client:
            raise RuntimeError("Embedder client not initialized")
        return self.embedder_client
    

