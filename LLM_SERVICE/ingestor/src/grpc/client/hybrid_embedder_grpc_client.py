from typing import Any, Dict, List
import grpc  # type: ignore
from src.core.utils import EnvTools
from loguru import logger

from protobuf_stubs import hybrid_embedder_pb2, hybrid_embedder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from pydantic_schemas.ingest import Chunk, EmbeddedChunk


class HybridEmbedderGrpcClient:
    def __init__(
        self,
        channel: grpc.Channel,
        service_name: str
        ) -> None:
        self.channel = channel
        self.service_name: str = service_name
        self.stub = hybrid_embedder_pb2_grpc.HybridEmbedderServiceStub(self.channel)
        self.batch_size: int  = int(EnvTools.required_load_env_var("HYBRID_EMBEDDER_EMBED_BATCH_MAX_SIZE"))
        self.embed_dims: int  = int(EnvTools.required_load_env_var("HYBRID_EMBEDDER_DIMENSIONS"))


    async def health_check(self) -> Dict[str, Any]:
        request = hybrid_embedder_pb2.HealthRequest()
        GrpcTools.validate_proto(request)
        
        try:
            response = await self.stub.Health(request, timeout=3)
            
            GrpcTools.validate_proto(response)
            return GrpcTools.proto_to_dict(response)

        except grpc.RpcError as ex:
            logger.error(f"{self.service_name} healthcheck failed: {ex}")
            raise


    async def embed_text_dense(
        self,
        text: str
    ) -> Dict[str, Any]:
        request = hybrid_embedder_pb2.DenseEmbedRequest(text=text)
        GrpcTools.validate_proto(request)
        
        try:
            response = await self.stub.DenseEmbed(request)
            
            if not response.success:
                raise Exception(f"Dense embedding failed: {response.error}")
            
            # GrpcTools.validate_proto(response)

            result = GrpcTools.proto_to_dict(response)

            logger.debug(f"Dense embedding result: success={result.get('success')}, vector_len={len(result.get('vector', []))}")
            return result

        except grpc.RpcError as ex:
            logger.error(f"Dense embed text failed: {ex}")
            raise


    async def embed_text_sparse(
        self,
        text: str
    ) -> Dict[str, Any]:
        request = hybrid_embedder_pb2.SparseEmbedRequest(text=text)
        GrpcTools.validate_proto(request)
        
        try:
            response = await self.stub.SparseEmbed(request)
            
            if not response.success:
                raise Exception(f"Sparse embedding failed: {response.error}")
            
            # GrpcTools.validate_proto(response)

            result = GrpcTools.proto_to_dict(response)

            logger.debug(f"Sparse embedding result: success={result.get('success')}, indices_len={len(result.get('indices', []))}")
            return result

        except grpc.RpcError as ex:
            logger.error(f"Sparse embed text failed: {ex}")
            raise


    async def embed_batch_dense(
        self,
        texts: list[str]
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
            request = hybrid_embedder_pb2.DenseEmbedBatchRequest(texts=batch_texts)
            
            GrpcTools.validate_proto(request)
            response = await self.stub.DenseEmbedBatch(request, timeout=60)
            
            batch_items = [GrpcTools.proto_to_dict(item) for item in response.items]
            all_items.extend(batch_items)

        successful_items = [item for item in all_items if item.get("success", False)]
        if not successful_items:
            raise Exception("No successful dense embeddings returned")

        return all_items + failed_results


    async def embed_batch_sparse(
        self,
        texts: list[str]
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
                    "indices": [],
                    "values": [],
                    "success": False,
                    "error": "Text too short or empty"
                })
        
        if not valid_texts:
            return failed_results

        all_items = []

        for i in range(0, len(valid_texts), self.batch_size):
            batch_texts = valid_texts[i:i + self.batch_size]

            request = hybrid_embedder_pb2.SparseEmbedBatchRequest(texts=batch_texts)
            
            GrpcTools.validate_proto(request)
            response = await self.stub.SparseEmbedBatch(request, timeout=60)
            
            batch_items = [GrpcTools.proto_to_dict(item) for item in response.items]
            all_items.extend(batch_items)

        successful_items = [item for item in all_items if item.get("success", False)]
        
        if not successful_items:
            raise Exception("No successful sparse embeddings returned")

        return all_items + failed_results


    async def embed_chunks(
        self,
        chunks: List[Chunk]
    ) -> List[EmbeddedChunk]:
        """
        Embeds a list of Chunk objects by extracting their text content.
        Returns EmbeddedChunk objects with dense and sparse vector embeddings and metadata.
        """
        texts = [chunk.text for chunk in chunks]
        
        dense_embeddings = await self.embed_batch_dense(texts)
        sparse_embeddings = await self.embed_batch_sparse(texts)
        
        if len(dense_embeddings) != len(chunks) or len(sparse_embeddings) != len(chunks):
            raise RuntimeError(f"Embedding count mismatch: expected {len(chunks)}, got dense={len(dense_embeddings)}, sparse={len(sparse_embeddings)}")
        
        result = []

        for chunk, dense_emb, sparse_emb in zip(chunks, dense_embeddings, sparse_embeddings):
            if (dense_emb.get("success", False) and dense_emb.get("vector") and
                sparse_emb.get("success", False) and sparse_emb.get("indices") and sparse_emb.get("values")):
                
                sparse_vector = {}

                for idx, val in zip(sparse_emb["indices"], sparse_emb["values"]):
                    sparse_vector[str(idx)] = val
                
                embedded_chunk = EmbeddedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    dense_vector=dense_emb["vector"],
                    sparse_vector=sparse_vector,
                    meta={
                        **chunk.meta,
                        "pages": chunk.pages,
                    }
                )

                result.append(embedded_chunk)

            else:
                error_msg = "Unknown embedding error"
                if not dense_emb.get("success", False):
                    error_msg = f"Dense embedding failed: {dense_emb.get('error', 'Unknown error')}"

                elif not sparse_emb.get("success", False):
                    error_msg = f"Sparse embedding failed: {sparse_emb.get('error', 'Unknown error')}"
                
                embedded_chunk = EmbeddedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    dense_vector=[],
                    sparse_vector={},
                    meta={
                        **chunk.meta,
                        "pages": chunk.pages,
                        "error": error_msg
                    }
                )

                result.append(embedded_chunk)
        
        return result

