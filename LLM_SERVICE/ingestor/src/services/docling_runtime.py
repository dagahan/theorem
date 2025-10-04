from __future__ import annotations
from src.core.utils import EnvTools
from loguru import logger


def select_device_for_ingestor() -> None:
    want = (EnvTools.load_env_var("INGESTOR_DEVICE") or "cpu").lower()
    
    tokenizers_parallelism = EnvTools.required_load_env_var("DOCLING_TOKENIZERS_PARALLELISM")
    pytorch_mps_fallback = EnvTools.required_load_env_var("DOCLING_PYTORCH_ENABLE_MPS_FALLBACK") 

    if want != "cuda":
        EnvTools.set_env_var("CUDA_VISIBLE_DEVICES", "")
        EnvTools.set_env_var("PYTORCH_ENABLE_MPS_FALLBACK", pytorch_mps_fallback)

    EnvTools.set_env_var("TOKENIZERS_PARALLELISM", tokenizers_parallelism)

    logger.info(f"ingestor device: {"cuda" if want == "cuda" else "cpu"}, tokenizers_parallelism: {tokenizers_parallelism}")

        