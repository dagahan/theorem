from __future__ import annotations
from typing import List, Tuple, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.models import Candidate

class DedupService:
    def __init__(self, keep_per_paragraph: int = 2, near_chunk_window: int = 2) -> None:
        self.keep_per_paragraph = keep_per_paragraph
        self.near_chunk_window = near_chunk_window

    def deduplicate(self, items: List["Candidate"]) -> List["Candidate"]:
        by_doc_par: Dict[Tuple[str, int], List["Candidate"]] = {}
        for c in items:
            doc, par, ch = c.key
            by_doc_par.setdefault((doc, par), []).append(c)

        out: List["Candidate"] = []
        for (doc, par), arr in by_doc_par.items():
            arr.sort(key=lambda x: x.score_total, reverse=True)
            kept: List["Candidate"] = []
            seen_chunks: List[int] = []
            for cand in arr:
                ch = cand.key[2]
                if any(abs(ch - s) <= self.near_chunk_window for s in seen_chunks):
                    continue
                kept.append(cand)
                seen_chunks.append(ch)
                if len(kept) >= self.keep_per_paragraph:
                    break
            out.extend(kept)

        out.sort(key=lambda x: x.score_total, reverse=True)
        return out