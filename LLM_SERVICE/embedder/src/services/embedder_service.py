from typing import Iterator, Optional, Any

import grpc
import numpy as np
import torch
from loguru import logger
from sentence_transformers import SentenceTransformer

from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from src.core.utils import EnvTools
from src.grpc.grpc_utils import GrpcTools


grpc_tools = GrpcTools()


def _to_f32_list(x: np.ndarray) -> list[float]:
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    return x.tolist()  # type: ignore[no-any-return]


class EmbedderService(embedder_pb2_grpc.EmbedderServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self.model_name: str = EnvTools.required_load_env_var("EMBEDDER_MODEL_NAME")
        self.batch_size: int = int(EnvTools.required_load_env_var("EMBEDDER_BATCH_SIZE"))

        torch.set_num_threads(int(EnvTools.required_load_env_var("TORCH_NUM_THREADS")))
        torch.set_num_interop_threads(1)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder_model: Optional[SentenceTransformer] = None
        self.dimensions: Any = None
        self._load_model()


    def _load_model(self) -> None:
        try:
            logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
            model = SentenceTransformer(self.model_name, device=self.device)

            with torch.inference_mode():
                _ = model.encode(["warmup"], batch_size=1, convert_to_numpy=True)

            dim = model.get_sentence_embedding_dimension()
            env_dimensions = int(EnvTools.required_load_env_var("EMBEDDER_DIMENSIONS"))
            if dim != env_dimensions:
                raise RuntimeError(
                    f"Embedder model dimensions mismatch:\n"
                    f"  model dim = {dim}\n"
                    f"  env   dim = {env_dimensions}"
                )

            self.embedder_model = model
            self.dimensions = dim

            logger.info(f"Embedder model is ready. dim={self.dimensions}, "
                        f"batch_size={self.batch_size}")

        except Exception as e:
            logger.exception(f"Failed to load model: {e}")
            raise


    @grpc_tools.log_grpc_request("Health")
    def Health(
        self,
        request: embedder_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            if self.embedder_model is None:
                response = embedder_pb2.HealthResponse(status="unhealthy", model_id="", dim=0)
                grpc_tools.validate_proto(response, context)
                return response
            else:
                dim = self.embedder_model.get_sentence_embedding_dimension()
                response = embedder_pb2.HealthResponse(
                    status="healthy",
                    model_id=self.model_name,
                    dim=dim,
                )
                grpc_tools.validate_proto(response, context)
                return response

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return embedder_pb2.HealthResponse(status="unhealthy", model_id="", dim=0)


    @grpc_tools.log_grpc_request("Embed")
    def Embed(
        self,
        request: embedder_pb2.EmbedRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.EmbedResponse:
        try:
            grpc_tools.validate_proto(request, context)

            if not self.embedder_model:
                return embedder_pb2.EmbedResponse(success=False, error="Model not loaded")

            text = request.text.strip()
            if not text:
                return embedder_pb2.EmbedResponse(success=False, error="Empty text")

            with torch.inference_mode():
                vec = self.embedder_model.encode(
                    text,
                    batch_size=1,
                    convert_to_numpy=True,
                    normalize_embeddings=request.normalize,
                    show_progress_bar=False,
                )

            response = embedder_pb2.EmbedResponse(vector=_to_f32_list(vec), success=True)
            grpc_tools.validate_proto(response, context)

            return response

        except Exception as e:
            logger.exception("Embed failed")
            return embedder_pb2.EmbedResponse(success=False, error=str(e))


    @grpc_tools.log_grpc_request("Embedbatch")
    def Embedbatch(
        self,
        request: embedder_pb2.EmbedBatchRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.EmbedBatchResponse:
        try:
            grpc_tools.validate_proto(request, context)
            
            if not self.embedder_model:
                response = embedder_pb2.EmbedBatchResponse(items=[])
                grpc_tools.validate_proto(response, context)
                return response

            texts = [t.strip() for t in request.texts if t.strip()]
            if not texts:
                response = embedder_pb2.EmbedBatchResponse(items=[])
                grpc_tools.validate_proto(response, context)
                return response

            with torch.inference_mode():
                vecs = self.embedder_model.encode(
                    texts,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=request.normalize,
                    show_progress_bar=False,
                )

            items = [embedder_pb2.EmbedResponse(vector=_to_f32_list(v), success=True) for v in vecs]
            response = embedder_pb2.EmbedBatchResponse(items=items)
            grpc_tools.validate_proto(response, context)
            return response

        except Exception as e:
            logger.exception("EmbedBatch failed")
            response = embedder_pb2.EmbedBatchResponse(items=[])
            grpc_tools.validate_proto(response, context)
            return response
    
