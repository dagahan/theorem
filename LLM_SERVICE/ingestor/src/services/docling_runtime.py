from __future__ import annotations
from src.core.utils import EnvTools
from loguru import logger


def select_device_for_ingestor() -> None:
    want = (EnvTools.load_env_var("INGESTOR_DEVICE") or "cpu").lower()

    if want != "cuda":
        EnvTools.set_env_var("CUDA_VISIBLE_DEVICES", "")
        EnvTools.set_env_var("PYTORCH_ENABLE_MPS_FALLBACK", "1")

    EnvTools.set_env_var("TOKENIZERS_PARALLELISM", "false")

    logger.info(f"ingestor device: {"cuda" if want == "cuda" else "cpu"}")

        