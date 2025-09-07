import os
from typing import Iterator, Optional

import grpc
import numpy as np
import torch
from loguru import logger
from sentence_transformers import SentenceTransformer
from protovalidate import Validator, ValidationError
import google.protobuf.message

from protobuf_stubs import embedder_pb2, embedder_pb2_grpc
from src.core.utils import EnvTools


def _to_f32_list(x: np.ndarray) -> list[float]:
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    return x.tolist()  # type: ignore[no-any-return]


class EmbedderService(embedder_pb2_grpc.EmbedderServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self.model_name: str = EnvTools.required_load_env_var("MODEL_NAME")
        self.batch_size: int = int(EnvTools.required_load_env_var("EMBEDDER_BATCH_SIZE"))
        self.validator = Validator()

        torch.set_num_threads(int(EnvTools.required_load_env_var("TORCH_NUM_THREADS")))
        torch.set_num_interop_threads(1)
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model: Optional[SentenceTransformer] = None
        self._load_model()


    def _load_model(self) -> None:
        try:
            logger.info(f"Loading embedding model: {self.model_name} on {self.device}")
            model = SentenceTransformer(self.model_name, device=self.device)

            with torch.inference_mode():
                _ = model.encode(["warmup"], batch_size=1, convert_to_numpy=True)
            self.model = model
            logger.info(f"Model ready. dim={self.model.get_sentence_embedding_dimension()}, "
                        f"batch={self.batch_size}")

        except Exception as e:
            logger.exception(f"Failed to load model: {e}")
            raise


    def _validate_in(
        self,
        msg: google.protobuf.message.Message,
        ctx: grpc.ServicerContext
    ) -> None:
        try:
            self.validator.validate(msg)
        except ValidationError as e:
            ctx.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))


    def _validate_out(
        self,
        msg: google.protobuf.message.Message,
        ctx: grpc.ServicerContext
    ) -> None:
        if EnvTools.required_load_env_var("VALIDATE_OUTBOUND") != "1":
            return
        try:
            self.validator.validate(msg)
        except ValidationError as e:
            logger.error(f"Response violates proto constraints: {e}")
            ctx.abort(grpc.StatusCode.INTERNAL, "internal schema violation")


    def Health(
        self,
        request: embedder_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.HealthResponse:
        try:
            if not self.model:
                return embedder_pb2.HealthResponse(status="unhealthy", model_id="", dim=0)
            return embedder_pb2.HealthResponse(
                status="healthy",
                model_id=self.model_name,
                dim=self.model.get_sentence_embedding_dimension(),
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return embedder_pb2.HealthResponse(status="unhealthy", model_id="", dim=0)


    def Embed(
        self,
        request: embedder_pb2.EmbedRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.EmbedResponse:
        try:
            self._validate_in(request, context)

            if not self.model:
                return embedder_pb2.EmbedResponse(success=False, error="Model not loaded")

            text = request.text.strip()
            if not text:
                return embedder_pb2.EmbedResponse(success=False, error="Empty text")

            with torch.inference_mode():
                vec = self.model.encode(
                    text,
                    batch_size=1,
                    convert_to_numpy=True,
                    normalize_embeddings=request.normalize,
                    show_progress_bar=False,
                )

            response = embedder_pb2.EmbedResponse(vector=_to_f32_list(vec), success=True)
            self._validate_out(response, context)

            return response

        except Exception as e:
            logger.exception("Embed failed")
            return embedder_pb2.EmbedResponse(success=False, error=str(e))


    def EmbedBatch(
        self,
        request: embedder_pb2.EmbedBatchRequest,
        context: grpc.ServicerContext,
    ) -> embedder_pb2.EmbedBatchResponse:
        try:
            self._validate_in(request, context)
            
            if not self.model:
                response = embedder_pb2.EmbedBatchResponse(items=[])
                self._validate_out(response, context)
                return response

            texts = [t.strip() for t in request.texts if t.strip()]
            if not texts:
                response = embedder_pb2.EmbedBatchResponse(items=[])
                self._validate_out(response, context)
                return response

            with torch.inference_mode():
                vecs = self.model.encode(
                    texts,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=request.normalize,
                    show_progress_bar=False,
                )

            items = [embedder_pb2.EmbedResponse(vector=_to_f32_list(v), success=True) for v in vecs]
            response = embedder_pb2.EmbedBatchResponse(items=items)
            self._validate_out(response, context)
            return response

        except Exception as e:
            logger.exception("EmbedBatch failed")
            response = embedder_pb2.EmbedBatchResponse(items=[])
            self._validate_out(response, context)
            return response
    

    def EmbedStream(
        self,
        request: embedder_pb2.EmbedStreamRequest,
        context: grpc.ServicerContext,
    ) -> Iterator[embedder_pb2.EmbedStreamResponse]:
        try:
            self._validate_in(request, context)
            
            if not self.model:
                context.abort(grpc.StatusCode.UNAVAILABLE, "Model not loaded")

            texts = [t.strip() for t in request.texts if t.strip()]
            if not texts:
                return

            with torch.inference_mode():
                for t in texts:
                    try:
                        if self.model is None:
                            continue
                        v = self.model.encode(
                            t,
                            batch_size=1,
                            convert_to_numpy=True,
                            normalize_embeddings=request.normalize,
                            show_progress_bar=False,
                        )
                        response = embedder_pb2.EmbedStreamResponse(vector=_to_f32_list(v), success=True)
                        self._validate_out(response, context)
                        yield response

                    except Exception as e:
                        logger.error(f"Stream item failed: {e}")
                        response = embedder_pb2.EmbedStreamResponse(success=False, error=str(e))
                        self._validate_out(response, context)
                        yield response

        except Exception as e:
            logger.exception("EmbedStream failed")
            context.abort(grpc.StatusCode.INTERNAL, str(e))
