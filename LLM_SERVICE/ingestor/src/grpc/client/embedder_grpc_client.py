from typing import Any, Dict, List
import grpc  # type: ignore
from src.core.utils import EnvTools
from loguru import logger

from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.data_classes.data_classes import Chunk, EmbeddedChunk


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
        self.embed_dims: int  = int(EnvTools.required_load_env_var("EMBEDDER_DIMENSIONS"))


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
                    "vector": [0.0] * self.embed_dims,
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

        successful_items = [item for item in all_items if item.get("success", False)]
        if not successful_items:
            raise Exception("No successful embeddings returned")

        return all_items + failed_results


    async def embed_chunks(
        self,
        chunks: List[Chunk]
    ) -> List[EmbeddedChunk]:
        """
        Embeds a list of Chunk objects by extracting their text content.
        Returns EmbeddedChunk objects with vector embeddings and metadata.
        """
        texts = [chunk.text for chunk in chunks]
        embeddings = await self.embed_batch(texts, normalize=True)
        
        if len(embeddings) != len(chunks):
            raise RuntimeError(f"Embedding count mismatch: expected {len(chunks)}, got {len(embeddings)}")
        
        # Combine embeddings with chunk metadata
        result = []
        for chunk, embedding in zip(chunks, embeddings):
            if embedding.get("success", False) and embedding.get("vector"):
                embedded_chunk = EmbeddedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    vector=embedding["vector"],
                    metadata={
                        **chunk.meta,
                        "parent_type": chunk.parent_type,
                        "pages": chunk.pages,
                        "parent_page_anchor": chunk.parent_page_anchor
                    }
                )
                result.append(embedded_chunk)
            else:
                # Create failed embedded chunk
                embedded_chunk = EmbeddedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    vector=[],
                    metadata={
                        **chunk.meta,
                        "parent_type": chunk.parent_type,
                        "pages": chunk.pages,
                        "parent_page_anchor": chunk.parent_page_anchor,
                        "error": embedding.get("error", "Unknown embedding error")
                    }
                )
                result.append(embedded_chunk)
        
        return result


