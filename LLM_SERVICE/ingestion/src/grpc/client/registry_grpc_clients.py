"""
Registry for gRPC clients used by ingestion service.
"""

import grpc  # type: ignore
from loguru import logger

from protobuf_stubs import embedder_pb2_grpc
from src.core.utils import EnvTools


class RegistryGrpcClients:
    """Registry for gRPC clients."""
    
    def __init__(self) -> None:
        self.embedder_stub = None
        self._init_clients()
    
    def _init_clients(self) -> None:
        """Initialize gRPC clients."""
        try:
            # Embedder client
            embedder_host = EnvTools.load_env_var("EMBEDDER_HOST") or "embedder"
            embedder_port = EnvTools.load_env_var("EMBEDDER_PORT") or "50051"
            
            embedder_channel = grpc.insecure_channel(f"{embedder_host}:{embedder_port}")
            self.embedder_stub = embedder_pb2_grpc.EmbedderServiceStub(embedder_channel)
            
            logger.info(f"gRPC clients initialized. Embedder: {embedder_host}:{embedder_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize gRPC clients: {e}")
            raise
    
    def get_embedder_stub(self) -> embedder_pb2_grpc.EmbedderServiceStub:
        """Get embedder service stub."""
        return self.embedder_stub


grpc_clients = RegistryGrpcClients()


