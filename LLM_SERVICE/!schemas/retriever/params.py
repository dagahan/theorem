from __future__ import annotations

from pydantic import BaseModel


class FusionWeights(BaseModel):  # type: ignore[misc]
    nn: float = 0.70
    bm25: float = 0.20
    rrf: float = 0.10


class PipelineLimits(BaseModel):  # type: ignore[misc]
    ann_top_k: int = 200
    nn_top_k: int = 80
    fusion_pool_cap: int = 300
    final_top_k: int = 25


class MmrParams(BaseModel):  # type: ignore[misc]
    diversity_lambda: float = 0.55
    mmr_pool_k: int = 60

