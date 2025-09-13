from typing import Any, Dict, List
import grpc  # type: ignore
from src.core.utils import EnvTools
from loguru import logger

from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools


class EmbedderGrpcClient:
    def __init__(
        self,
        channel: grpc.Channel,
        service_name: str
        ) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.stub = embedder_pb2_grpc.EmbedderServiceStub(self.channel)
        self.batch_size: int  = int(EnvTools.required_load_env_var("EMBEDDER_EMBED_BATCH_MAX_SIZE"))


    async def health_check(self) -> Dict[str, Any]:
        request = embedder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)
        
        try:
            response = self.stub.Health(request, timeout=3)
            
            GrpcTools.validate_proto(response)

            return GrpcTools.proto_to_dict(response)

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            raise


    async def embed_text(
        self,
        text: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        request = embedder_pb2.EmbedRequest(text=text, normalize=normalize)
        GrpcTools.validate_proto(request)
        
        try:
            response = self.stub.Embed(request)
            
            if not response.success:
                raise Exception(f"Embedding failed: {response.error}")
            
            GrpcTools.validate_proto(response)

            result = GrpcTools.proto_to_dict(response)

            logger.debug(f"Embedding result: success={result.get('success')}, vector_len={len(result.get('vector', []))}")
            return result

        except grpc.RpcError as ex:
            logger.error(f"Embed text failed: {ex}")
            raise


    async def embed_batch(
        self,
        texts: list[str],
        normalize: bool = True
    ) -> list[Dict[str, Any]]:
        all_items: list[Dict[str, Any]] = []

        for i in range(0, len(texts), self.batch_size):
            part = texts[i:i+ self.batch_size]
            request = embedder_pb2.EmbedBatchRequest(texts=part, normalize=normalize)

            GrpcTools.validate_proto(request)

            response = self.stub.EmbedBatch(request, timeout=60)

            all_items.extend([GrpcTools.proto_to_dict(it) for it in response.items])

        if not any(item.get("success") for item in all_items):
            raise Exception("No successful embeddings returned")

        return all_items


