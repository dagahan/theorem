from typing import Iterator, Any

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
        self.embed_batch_size: int = int(EnvTools.required_load_env_var("EMBEDDER_EMBED_BATCH_MAX_SIZE"))

        torch.set_num_threads(int(EnvTools.required_load_env_var("TORCH_NUM_THREADS")))
        torch.set_num_interop_threads(1)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embedder_model: SentenceTransformer | None = None
        
        self.dimensions: Any = None
        self._load_model()


    def _load_model(self) -> None:
        try:
            logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
            model = SentenceTransformer(self.model_name, device=self.device)

            try:
                model.max_seq_length = min(getattr(model, "max_seq_length", 512), 256)
            except Exception:
                pass

            with torch.inference_mode():
                _ = model.encode(["warmup"], batch_size=1, convert_to_numpy=True, show_progress_bar=False)

            dim = model.get_sentence_embedding_dimension()
            env_dimensions = int(EnvTools.required_load_env_var("EMBEDDER_DIMENSIONS"))
            if dim != env_dimensions:
                raise RuntimeError(f"Embedder model dimensions mismatch:\n  model dim = {dim}\n  env   dim = {env_dimensions}")

            self.embedder_model = model
            self.dimensions = dim
            logger.info(f"Embedder model is ready. dim={self.dimensions}, embed_batch_size={self.embed_batch_size}")

        except Exception as ex:
            logger.exception(f"Failed to load model: {ex}")
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

        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return embedder_pb2.HealthResponse(status="unhealthy", model_id="", dim=0)


    @grpc_tools.log_grpc_request("Embed")
    def Embed(
        self,
        request: embedder_pb2.EmbedRequest,
        context: grpc.ServicerContext
    ) -> embedder_pb2.EmbedResponse:
        try:
            grpc_tools.validate_proto(request, context)

            if not self.embedder_model:
                return embedder_pb2.EmbedResponse(success=False, error="Model not loaded")

            text = request.text.strip()
            if not text:
                return embedder_pb2.EmbedResponse(success=False, error="Empty text")

            assert self.embedder_model is not None
            model: SentenceTransformer = self.embedder_model
            use_amp = torch.cuda.is_available()
            try:
                with torch.inference_mode(), (torch.cuda.amp.autocast() if use_amp else torch.cpu.amp.autocast(enabled=False)):
                    vector = model.encode(text, batch_size=1, convert_to_numpy=True,
                                       normalize_embeddings=request.normalize, show_progress_bar=False)

            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                vector = model.encode(text, batch_size=1, convert_to_numpy=True, normalize_embeddings=request.normalize,
                                   show_progress_bar=False, device="cpu")

            return embedder_pb2.EmbedResponse(vector=_to_f32_list(vector), success=True)

        except Exception as ex:
            logger.exception("Embed failed")
            return embedder_pb2.EmbedResponse(success=False, error=str(ex))


    @grpc_tools.log_grpc_request("EmbedBatch")
    def EmbedBatch(
        self,
        request: embedder_pb2.EmbedBatchRequest,
        context: grpc.ServicerContext
    ) -> embedder_pb2.EmbedBatchResponse:
        try:
            grpc_tools.validate_proto(request, context)

            if not self.embedder_model:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Model not loaded")

            texts = [t.strip() for t in request.texts if t and t.strip()]
            if not texts:
                return embedder_pb2.EmbedBatchResponse(items=[])

            assert self.embedder_model is not None
            model: SentenceTransformer = self.embedder_model
            bs = max(1, min(self.embed_batch_size, len(texts)))
            use_amp = torch.cuda.is_available()

            while True:
                try:
                    with torch.inference_mode(), (torch.cuda.amp.autocast() if use_amp else torch.cpu.amp.autocast(enabled=False)):
                        vectors = model.encode(
                            texts,
                            batch_size=bs,
                            convert_to_numpy=True,
                            normalize_embeddings=request.normalize,
                            show_progress_bar=False,
                        )
                    break

                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    if bs > 1:
                        bs = max(1, bs // 2)
                        continue

                    # батч уже 1 — фолбэк на CPU
                    vectors = model.encode(
                        texts,
                        batch_size=1,
                        convert_to_numpy=True,
                        normalize_embeddings=request.normalize,
                        show_progress_bar=False,
                        device="cpu",
                    )
                    break

            items = [embedder_pb2.EmbedResponse(vector=_to_f32_list(v), success=True) for v in vectors]
            return embedder_pb2.EmbedBatchResponse(items=items)

        except grpc.RpcError:
            raise

        except Exception as ex:
            context.abort(grpc.StatusCode.INTERNAL, str(ex))
    
