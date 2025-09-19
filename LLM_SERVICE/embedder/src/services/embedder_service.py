from typing import Any

import numpy as np
import torch
from loguru import logger
from sentence_transformers import SentenceTransformer

from src.core.utils import EnvTools
from src.domain.models import EmbeddingRequest, EmbeddingResult, BatchEmbeddingRequest, BatchEmbeddingResult, HealthStatus


def _to_f32_list(x: np.ndarray) -> list[float]:
    if x.dtype != np.float32:
        x = x.astype(np.float32, copy=False)
    return x.tolist()  # type: ignore[no-any-return]


class EmbedderService:
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


    def get_health_status(self) -> HealthStatus:
        try:
            if self.embedder_model is None:
                return HealthStatus(status="unhealthy", model_id="", dimensions=0)
            else:
                dim = self.embedder_model.get_sentence_embedding_dimension()
                return HealthStatus(
                    status="healthy",
                    model_id=self.model_name,
                    dimensions=dim,
                )

        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return HealthStatus(status="unhealthy", model_id="", dimensions=0)


    def embed_text(self, request: EmbeddingRequest) -> EmbeddingResult:
        try:
            if not self.embedder_model:
                return EmbeddingResult(text=request.text, vector=[], success=False, error="Model not loaded")

            text = request.text.strip()
            if not text:
                return EmbeddingResult(text=request.text, vector=[], success=False, error="Empty text")

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

            return EmbeddingResult(text=request.text, vector=_to_f32_list(vector), success=True)

        except Exception as ex:
            logger.exception("Embed failed")
            return EmbeddingResult(text=request.text, vector=[], success=False, error=str(ex))


    def embed_batch(self, request: BatchEmbeddingRequest) -> BatchEmbeddingResult:
        try:
            if not self.embedder_model:
                return BatchEmbeddingResult(results=[], success=False, error="Model not loaded")

            texts = [t.strip() for t in request.texts if t and t.strip()]
            if not texts:
                return BatchEmbeddingResult(results=[], success=True)

            assert self.embedder_model is not None
            model: SentenceTransformer = self.embedder_model
            batch_size = max(1, min(self.embed_batch_size, len(texts)))
            use_amp = torch.cuda.is_available()

            while True:
                try:
                    with torch.inference_mode(), (torch.cuda.amp.autocast() if use_amp else torch.cpu.amp.autocast(enabled=False)):
                        vectors = model.encode(
                            texts,
                            batch_size=batch_size,
                            convert_to_numpy=True,
                            normalize_embeddings=request.normalize,
                            show_progress_bar=False,
                        )
                    break

                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    if batch_size > 1:
                        batch_size = max(1, batch_size // 2)
                        continue

                    vectors = model.encode(
                        texts,
                        batch_size=1,
                        convert_to_numpy=True,
                        normalize_embeddings=request.normalize,
                        show_progress_bar=False,
                        device="cpu",
                    )
                    break

            results = [
                EmbeddingResult(text=text, vector=_to_f32_list(vector), success=True)
                for text, vector in zip(texts, vectors)
            ]
            return BatchEmbeddingResult(results=results, success=True)

        except Exception as ex:
            logger.exception("Embed batch failed")
            return BatchEmbeddingResult(results=[], success=False, error=str(ex))
    
