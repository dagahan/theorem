from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from src.pydantic_schemas.retriever import Candidate

DocKey = Tuple[str, int, int]


class CandidateMergeService:
    @staticmethod
    def to_key(item: "Candidate") -> DocKey:
        return item.key

    def merge_and_deduplicate(
        self,
        dense_hits: List["Candidate"],
        sparse_hits: List["Candidate"]
    ) -> List["Candidate"]:
        by_key: Dict[DocKey, "Candidate"] = {}
        
        for item in dense_hits + sparse_hits:
            key = self.to_key(item)
            old = by_key.get(key)
            if old is None or float(item.score_ann + item.score_bm25) > float(old.score_ann + old.score_bm25):
                by_key[key] = item
        
        return list(by_key.values())
