from __future__ import annotations

import torch
from loguru import logger
from FlagEmbedding import BGEM3FlagModel

from src.core.utils import EnvTools


class ModelLoader:
    def __init__(self) -> None:
        self.model_name: str = EnvTools.required_load_env_var("HYBRID_EMBEDDER_MODEL_NAME")
        self.embed_batch_size: int = int(EnvTools.required_load_env_var("HYBRID_EMBEDDER_EMBED_BATCH_MAX_SIZE"))
        self.max_seq_length: int = int(EnvTools.required_load_env_var("HYBRID_EMBEDDER_MAX_SEQ_LENGTH"))

        torch.set_num_threads(int(EnvTools.required_load_env_var("TORCH_NUM_THREADS")))
        torch.set_num_interop_threads(1)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model: BGEM3FlagModel | None = None

        self.dimensions: int = -1
        self.sparse_vocab_size: int = -1


    def load_hybrid_embedder_model(self) -> None:
        try:
            logger.info(f"Loading hybrid embedding model: {self.model_name} on {self.device}")
            model = BGEM3FlagModel(
                self.model_name,
                use_fp16=torch.cuda.is_available()
            )

            _ = model.encode(
               ["warmup"],
                batch_size=1,
                max_length=min(16, self.max_seq_length),
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )

            self.dimensions = int(model.model.config.hidden_size)
            env_dimensions = int(EnvTools.required_load_env_var("HYBRID_EMBEDDER_DIMENSIONS"))

            if self.dimensions != env_dimensions:
                raise RuntimeError(
                    "Hybrid embedder model dimensions mismatch:\n"
                    f"  model dim = {self.dimensions}\n  env   dim = {env_dimensions}"
                )

            try:
                self.sparse_vocab_size = int(model.tokenizer.vocab_size)

            except Exception:
                self.sparse_vocab_size = -1

            self.model = model
            logger.info(
                f"Hybrid embedder is ready. dim={self.dimensions}, vocab={self.sparse_vocab_size}, "
                f"embed_batch_size={self.embed_batch_size}, max_len={self.max_seq_length}"
            )

        except Exception as ex:
            logger.exception(f"Failed to load BGEM3FlagModel: {ex}")
            raise



