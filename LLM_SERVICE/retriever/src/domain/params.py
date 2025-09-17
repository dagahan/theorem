from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FusionWeights:
    nn: float = 0.70
    bm25: float = 0.20
    rrf: float = 0.10


@dataclass(frozen=True)
class PipelineLimits:
    ann_top_k: int = 200
    nn_top_k: int = 80
    fusion_pool_cap: int = 300
    final_top_k: int = 25


@dataclass(frozen=True)
class MmrParams:
    diversity_lambda: float = 0.55
    mmr_pool_k: int = 60



    