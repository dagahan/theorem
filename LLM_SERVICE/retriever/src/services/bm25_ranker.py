from __future__ import annotations
import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, Final, List, Tuple
from src.services.vector_store_service import VectorStoreService
from src.services.text_normalize_service import TextNormalizeService
from src.services.synonym_service import SynonymService
from src.domain.models import Candidate, DocKey

class BM25Scorer:
    _DEFAULT_K1: Final[float] = 1.5
    _DEFAULT_B: Final[float] = 0.75
    _EPS: Final[float] = 1e-9

    def __init__(self, docs_tokens: List[List[str]], k1: float = _DEFAULT_K1, b: float = _DEFAULT_B) -> None:
        self.k1 = k1
        self.b = b
        self.n_docs = len(docs_tokens)
        self.lengths = [len(d) for d in docs_tokens]
        self.avg_len = sum(self.lengths) / max(1, self.n_docs)
        df: Counter[str] = Counter()
        for tks in docs_tokens:
            df.update(set(tks))
        self.idf: Dict[str, float] = {}
        for w, dfreq in df.items():
            self.idf[w] = math.log((self.n_docs - dfreq + 0.5) / (dfreq + 0.5) + 1.0)

    def score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        tf: Counter[str] = Counter(doc_tokens)
        L = len(doc_tokens)
        denom_norm = self.k1 * (1.0 - self.b + self.b * L / max(1, self.avg_len))
        s = 0.0
        for q in query_tokens:
            if q not in tf:
                continue
            s += self.idf.get(q, 0.0) * (tf[q] * (self.k1 + 1.0)) / (tf[q] + denom_norm + self._EPS)
        return s

class Bm25Ranker:
    _MAX_PAR_BY_DOC: Final[int] = 9

    def __init__(self) -> None:
        self.store = VectorStoreService()
        self.norm = TextNormalizeService()
        self.syn = SynonymService()
        self._word_re = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")

    async def rerank_with_bm25(
        self,
        collection_name: str,
        ann_candidates: List[Candidate],
        original_query: str,
        neighbor_window_size: int,
        max_results: int
    ) -> List[Candidate]:
        if not ann_candidates:
            return []

        by_doc: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        for c in sorted(ann_candidates, key=lambda x: -x.score_ann):
            doc, par, ch = c.key
            by_doc[doc].append((par, ch))

        contexts: List[Tuple[DocKey, str, List[int], Dict[str, Any]]] = []
        for doc_id, pairs in by_doc.items():
            for par_id, ch_id in pairs[: self._MAX_PAR_BY_DOC]:
                start = max(1, ch_id - neighbor_window_size)
                end = ch_id + neighbor_window_size
                window = await self.store.get_window_by_chunk_id(collection_name, doc_id, start, end)
                for chunk in window:
                    payload = chunk.get("payload", chunk)
                    key: DocKey = (str(payload["doc_id"]), int(payload["paragraph_id"]), int(payload["chunk_id"]))
                    text = payload.get("text", "")
                    pages = [int(p) for p in payload.get("pages", [])]
                    contexts.append((key, text, pages, payload))

        if not contexts:
            return []

        docs_tokens: List[List[str]] = []
        for _, text, _, _ in contexts:
            txt = self.norm.normalize_query_text(text)
            docs_tokens.append([w.lower() for w in self._word_re.findall(txt)])

        base_words = [w.lower() for w in self._word_re.findall(self.norm.normalize_query_text(original_query))]
        expanded = self.syn.expand_words_for_bm25(base_words)
        query_tokens = list(dict.fromkeys(base_words + expanded))

        scorer = BM25Scorer(docs_tokens)
        scored: List[Tuple[int, float]] = []
        for i, dt in enumerate(docs_tokens):
            scored.append((i, scorer.score(query_tokens, dt)))
        scored.sort(key=lambda x: x[1], reverse=True)

        out: List[Candidate] = []
        for rank, (idx, score) in enumerate(scored[:max_results], start=1):
            key, text, pages, payload = contexts[idx]
            out.append(Candidate(
                key=key,
                text=text,
                pages=pages,
                payload=payload,
                score_bm25=score,
                rank_bm25=rank
            ))
        return out