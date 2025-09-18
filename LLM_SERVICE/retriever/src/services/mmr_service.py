from __future__ import annotations
from typing import List, Dict, TYPE_CHECKING
import math
from src.adapters.embedder_adapter import EmbedderAdapter

if TYPE_CHECKING:
    from src.domain.models import Candidate


def _cos(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    num = sum(x*y for x, y in zip(a, b))
    da = math.sqrt(sum(x*x for x in a)) or 1e-9
    db = math.sqrt(sum(y*y for y in b)) or 1e-9
    return num / (da * db)


class MmrService:
    def __init__(self, diversity_lambda: float = 0.55) -> None:
        self.embedder = EmbedderAdapter()
        self.lmb = diversity_lambda


    async def reorder(
        self,
        query_text: str,
        items: List["Candidate"],
        k: int
    ) -> List["Candidate"]:
        if not items:
            return []
        pool = items[:k]
        qv = (await self.embedder.embed_text(query_text, normalize=True)).get("vector", [])
        c_vecs = [(await self.embedder.embed_text(c.text, normalize=True)).get("vector", []) for c in pool]

        selected: List[int] = []
        remaining: List[int] = list(range(len(pool)))

        while remaining and len(selected) < k:
            best_idx = None
            best_score = -1e9
            for i in remaining:
                rel = _cos(qv, c_vecs[i])
                div = 0.0
                if selected:
                    div = max(_cos(c_vecs[i], c_vecs[j]) for j in selected)
                mmr = self.lmb * rel - (1.0 - self.lmb) * div
                if mmr > best_score:
                    best_score = mmr
                    best_idx = i
            selected.append(best_idx)  # type: ignore
            remaining.remove(best_idx) # type: ignore

        return [pool[i] for i in selected] + [pool[i] for i in remaining]


