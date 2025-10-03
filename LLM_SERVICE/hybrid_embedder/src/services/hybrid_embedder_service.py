from __future__ import annotations

from typing import Dict, List, cast

import torch
from loguru import logger

from src.pydantic_schemas.hybrid_embedder.models import (
    DenseEmbedBatchRequest,
    DenseEmbedBatchResponse,
    DenseEmbedRequest,
    DenseEmbedResponse,
    HealthStatus,
    SparseEmbedBatchRequest,
    SparseEmbedBatchResponse,
    SparseEmbedRequest,
    SparseEmbedResponse,
)
from .model_loader import ModelLoader
from .vector_processor import VectorProcessor


class HybridEmbedderService:
    def __init__(self) -> None:
        self.model_loader = ModelLoader()
        self.model_loader.load_hybrid_embedder_model()
        self.vector_processor = VectorProcessor()


    def get_health_status(self) -> HealthStatus:
        try:
            if self.model_loader.model is None:
                return HealthStatus(
                    status="unhealthy",
                    model_id="",
                    dimensions=0,
                    sparse_vocab_size=-1,
                )

            return HealthStatus(
                status="healthy",
                model_id=self.model_loader.model_name,
                dimensions=self.model_loader.dimensions,
                sparse_vocab_size=self.model_loader.sparse_vocab_size,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error(f"Hybrid embedder health check failed: {exc}")
            return HealthStatus(
                status="unhealthy",
                model_id="",
                dimensions=0,
                sparse_vocab_size=-1
            )


    def _encode(
         self,
         texts: List[str],
         batch_size: int,
         want_dense: bool,
         want_sparse: bool,
     ) -> Dict[str, object]:
         assert self.model_loader.model is not None, "Model must be loaded"
         encoded = self.model_loader.model.encode(
             texts,
             batch_size=batch_size,
             max_length=self.model_loader.max_seq_length,
             return_dense=want_dense,
             return_sparse=want_sparse,
             return_colbert_vecs=False,
         )
         return cast("dict[str, object]", encoded)


    def _encode_with_oom_handling(
        self,
        texts: List[str],
        initial_batch_size: int,
        want_dense: bool,
        want_sparse: bool,
    ) -> Dict[str, object]:
        batch_size = initial_batch_size
        while True:
            try:
                return self._encode(texts, batch_size, want_dense, want_sparse)
            except torch.cuda.OutOfMemoryError:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                if batch_size > 1:
                    batch_size = max(1, batch_size // 2)
                    continue
                return self._encode(texts, 1, want_dense, want_sparse)


    def dense_embed(
        self,
        request: DenseEmbedRequest
    ) -> DenseEmbedResponse:
        if not self.model_loader.model:
            return DenseEmbedResponse(vector=[], success=False, error="Model not loaded")
        try:
            encode_result = self._encode_with_oom_handling(
                texts=[request.text],
                initial_batch_size=1,
                want_dense=True,
                want_sparse=False,
             )

            vector = self.vector_processor.extract_dense_vector(encode_result, 0)
            vector = self.vector_processor.l2_normalize(vector)

            return DenseEmbedResponse(vector=vector, success=True)
            
        except torch.cuda.OutOfMemoryError:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.exception("dense_embed OOM")

            return DenseEmbedResponse(
                vector=[],
                success=False,
                error="CUDA OOM"
            )

        except Exception as ex:  # noqa: BLE001
            logger.exception("dense_embed failed")
            return DenseEmbedResponse(
                vector=[],
                success=False,
                error=str(ex)
            )


    def dense_embed_batch(
        self,
        request: DenseEmbedBatchRequest
    ) -> DenseEmbedBatchResponse:
        responses = [self.dense_embed(DenseEmbedRequest(text=text)) for text in request.texts]

        success = all(item.success for item in responses)

        error = None

        if not success:
            error_messages = [item.error for item in responses if item.error]
            error = "; ".join(error_messages) if error_messages else "Batch embedding failed"

        return DenseEmbedBatchResponse(
            items=responses,
            success=success,
            error=error
        )



    def sparse_embed(
        self,
        request: SparseEmbedRequest
    ) -> SparseEmbedResponse:
        if not self.model_loader.model:
            return SparseEmbedResponse(
                indices=[],
                values=[],
                success=False,
                error="Model not loaded"
            )

        try:
            encode_result = self._encode_with_oom_handling(
                texts=[request.text],
                initial_batch_size=1,
                want_dense=False,
                want_sparse=True,
            )

            extracted = self.vector_processor.extract_sparse_vector(encode_result, 0)

            if extracted is None:
                return SparseEmbedResponse(indices=[], values=[], success=False, error="Empty sparse vector")
            indices, values = extracted

            return SparseEmbedResponse(indices=indices, values=values, success=True)

        except torch.cuda.OutOfMemoryError:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.exception("sparse_embed OOM")

            return SparseEmbedResponse(indices=[], values=[], success=False, error="CUDA OOM")

        except Exception as exc:  # noqa: BLE001
            logger.exception("sparse_embed failed")
            return SparseEmbedResponse(indices=[], values=[], success=False, error=str(exc))


    def sparse_embed_batch(
        self,
        request: SparseEmbedBatchRequest
    ) -> SparseEmbedBatchResponse:
        responses = [self.sparse_embed(SparseEmbedRequest(text=text)) for text in request.texts]

        success = all(item.success for item in responses)
        error = None

        if not success:
            error_messages = [item.error for item in responses if item.error]
            error = "; ".join(error_messages) if error_messages else "Batch embedding failed"

        return SparseEmbedBatchResponse(items=responses, success=success, error=error)


