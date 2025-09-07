import asyncio
from typing import List

import grpc
from loguru import logger
from sentence_transformers import SentenceTransformer

from src.core.config import ConfigLoader
from src.core.logging import InterceptHandler, LogSetup
from src.core.utils import EnvTools

import proto.embedder_pb2 as embedder_pb2
import proto.embedder_pb2_grpc as embedder_pb2_grpc


class EmbedderService(embedder_pb2_grpc.EmbedderServiceServicer):
    def __init__(self) -> None:
        self.config = ConfigLoader()
        self.model_name = EnvTools.get_env_var("EMBEDDER_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def EmbedText(self, request, context):
        try:
            if not self.model:
                return embedder_pb2.EmbedTextResponse(
                    success=False,
                    error="Model not loaded"
                )

            embedding = self.model.encode(request.text)
            embedding_list = embedding.tolist()

            return embedder_pb2.EmbedTextResponse(
                embedding=embedding_list,
                success=True
            )
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            return embedder_pb2.EmbedTextResponse(
                success=False,
                error=str(e)
            )

    def EmbedBatch(self, request, context):
        try:
            if not self.model:
                return embedder_pb2.EmbedBatchResponse(
                    success=False,
                    error="Model not loaded"
                )

            embeddings = self.model.encode(request.texts)
            results = []

            for embedding in embeddings:
                results.append(embedder_pb2.EmbeddingResult(
                    embedding=embedding.tolist(),
                    success=True
                ))

            return embedder_pb2.EmbedBatchResponse(
                results=results,
                success=True
            )
        except Exception as e:
            logger.error(f"Error embedding batch: {e}")
            return embedder_pb2.EmbedBatchResponse(
                success=False,
                error=str(e)
            )


class Service:
    def __init__(self) -> None:
        self.config = ConfigLoader()
        self.intercept_handler = InterceptHandler()
        self.logger_setup = LogSetup()
        self.service_name = self.config.get("project", "name")
        self.server = None

    async def run_service(self) -> None:
        self.logger_setup.configure()
        
        server = grpc.aio.server()
        embedder_pb2_grpc.add_EmbedderServiceServicer_to_server(EmbedderService(), server)
        
        host = EnvTools.get_service_ip(self.service_name)
        port = EnvTools.get_service_port(self.service_name)
        
        listen_addr = f"{host}:{port}"
        server.add_insecure_port(listen_addr)
        
        logger.info(f"Starting embedder service on {listen_addr}")
        
        await server.start()
        self.server = server
        
        try:
            await server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            await server.stop(grace=5.0)
            logger.info("Service stopped gracefully")


if __name__ == "__main__":
    try:
        service = Service()
        asyncio.run(service.run_service())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as error:
        logger.critical(f"Service crashed: {error}")
        import sys
        sys.exit(1)