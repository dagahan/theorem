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
            response = await self.stub.Health(request, timeout=3)
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
            response = await self.stub.Embed(request)
            
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
        valid_texts = []
        failed_results = []
        
        for text in texts:
            if len(text) >= 10 and text.strip():
                if len(text) > 8192:
                    text = text[:8192]
                valid_texts.append(text)
            else:
                failed_results.append({
                    "vector": [0.0] * 768,
                    "success": False,
                    "error": "Text too short or empty"
                })
        
        if not valid_texts:
            return failed_results

        all_items = []
        for i in range(0, len(valid_texts), self.batch_size):
            batch_texts = valid_texts[i:i + self.batch_size]
            request = embedder_pb2.EmbedBatchRequest(texts=batch_texts, normalize=normalize)
            
            GrpcTools.validate_proto(request)
            response = await self.stub.EmbedBatch(request, timeout=60)
            
            batch_items = [GrpcTools.proto_to_dict(item) for item in response.items]
            all_items.extend(batch_items)

        if not any(item.get("success") for item in all_items):
            raise Exception("No successful embeddings returned")

        return all_items + failed_results


