from __future__ import annotations

from pydantic import BaseModel


class HybridSearchParams(BaseModel):  # type: ignore[misc]
    semantic_top_k: int = 10
    lexical_top_k: int = 5
    final_top_k: int = 15
    rerank_pool_cap: int = 64

