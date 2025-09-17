from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, Final, List, Tuple
import math


DocKey = Tuple[str, int, int]  # (doc_id, page, chunk)


class FusionService:
    """
    Gluing candidates from ANN, BM25, and neuro-reranker.
    """

    _RRF_K: Final[int] = 60
    _EPS: Final[float] = 1e-9


    def fuse(
        self,
        ann: List[Dict[str, Any]],      # [{document_key, rank_position?, similarity_score, document_data}]
        bm25: List[Dict[str, Any]],     # [{document_key, rank_position?, bm25_score,    document_data}]
        nn: List[Dict[str, Any]],       # [{document_key, neural_score,                  document_data}]
        max_results: int = 25,
    ) -> List[Dict[str, Any]]:

        ann_rank = self._build_rank_map(ann, by="rank_position", fallback_sort_key=lambda x: -float(x.get("similarity_score", 0.0)))
        bm25_rank = self._build_rank_map(bm25, by="rank_position", fallback_sort_key=lambda x: -float(x.get("bm25_score", 0.0)))
        nn_score = {r["document_key"]: float(r.get("neural_score", 0.0)) for r in nn}

        ann_score_raw = {r["document_key"]: float(r.get("similarity_score", 0.0)) for r in ann}
        bm25_score_raw = {r["document_key"]: float(r.get("bm25_score", 0.0)) for r in bm25}

        # Пул всех ключей
        keys: List[DocKey] = list(self._union_keys([ann_rank, bm25_rank, nn_score]))

        # 2) RRF по ANN+BM25
        rrf = self._compute_rrf(keys, ann_rank, bm25_rank)

        # 3) Нормализация сигналов
        # ANN: если косинус уже в [-1,1], можно привести к [0,1], здесь используем min-max по пулу.
        ann_norm = self._minmax_map(ann_score_raw, keys)
        # BM25: log1p сглаживает хвост, затем min-max
        bm25_log = {k: math.log1p(bm25_score_raw.get(k, 0.0)) for k in keys}
        bm25_norm = self._minmax_map(bm25_log, keys)
        # RRF: используем перцентиль как [0,1] ранговую норму
        rrf_pct = self._percentile_map(rrf, keys)
        # NN: приводим к [0,1] (если прилетели логиты)
        nn_norm = self._nn_to_prob_map(nn_score, keys)

        # 4) Весовая смесь (локально заданные веса)
        w_nn, w_bm25, w_rrf = 0.70, 0.20, 0.10

        combined: List[Tuple[DocKey, float, float, float, float]] = []
        for k in keys:
            s_nn = nn_norm.get(k, 0.0)
            s_bm = bm25_norm.get(k, 0.0)
            s_rr = rrf_pct.get(k, 0.0)
            s_total = w_nn * s_nn + w_bm25 * s_bm + w_rrf * s_rr
            combined.append((k, s_total, s_nn, s_bm, s_rr))

        # 5) Сортировка с тай-брейками: total → NN → RRF
        combined.sort(key=lambda t: (t[1], t[2], t[4]), reverse=True)

        # 6) Сбор document_data (первый встретившийся источник фиксирует payload)
        doc_data: Dict[DocKey, Dict[str, Any]] = {}
        for src in (ann, bm25, nn):
            for r in src:
                doc_data.setdefault(r["document_key"], r.get("document_data", {}))

        # 7) Выход
        out: List[Dict[str, Any]] = []
        for k, s_total, s_nn, s_bm, s_rr in combined[:max_results]:
            out.append({
                "document_key": k,
                "document_data": doc_data.get(k, {}),
                "score": s_total,
                "score_nn": s_nn,
                "score_bm25": s_bm,
                "score_rrf": s_rr,
            })

        return out


    def _build_rank_map(
        self,
        items: List[Dict[str, Any]],
        by: str,
        fallback_sort_key: Callable[[Dict[str, Any]], float],
    ) -> Dict[DocKey, int]:
        """Вернёт ранги 1..N. Если ранги не даны, строим по сортировке."""
        if not items:
            return {}

        if any(by in x for x in items):
            # используем как есть, заменяя отсутствующие на большое число
            pairs = [(it["document_key"], int(it.get(by, 10**9))) for it in items]
            # нормализуем в строгие ранги
            pairs.sort(key=lambda p: p[1])
            return {k: i + 1 for i, (k, _) in enumerate(pairs)}
            
        # fallback: сортируем по ключу
        items_sorted = sorted(items, key=fallback_sort_key)
        return {it["document_key"]: i + 1 for i, it in enumerate(items_sorted)}


    def _union_keys(
        self,
        dicts: List[Dict[DocKey, Any]]
    ) -> List[DocKey]:
        keys: set[DocKey] = set()
        for d in dicts:
            keys.update(d.keys())
        return list(keys)


    def _compute_rrf(
        self,
        keys: List[DocKey],
        ann_rank: Dict[DocKey, int],
        bm25_rank: Dict[DocKey, int],
    ) -> Dict[DocKey, float]:
        rrf: Dict[DocKey, float] = {}
        for k in keys:
            r = 0.0
            if k in ann_rank:
                r += 1.0 / (self._RRF_K + ann_rank[k])
            if k in bm25_rank:
                r += 1.0 / (self._RRF_K + bm25_rank[k])
            rrf[k] = r

        return rrf


    def _minmax_map(
        self,
        values: Dict[DocKey, float],
        keys: List[DocKey]
    ) -> Dict[DocKey, float]:
        xs = [values.get(k, 0.0) for k in keys]
        vmin, vmax = (min(xs), max(xs)) if xs else (0.0, 1.0)
        if vmax - vmin < self._EPS:
            return {k: 0.0 for k in keys}
        return {k: (values.get(k, 0.0) - vmin) / (vmax - vmin) for k in keys}


    def _percentile_map(
        self,
        values: Dict[DocKey, float],
        keys: List[DocKey]
    ) -> Dict[DocKey, float]:
        arr = sorted(values.get(k, 0.0) for k in keys)
        n = len(arr) or 1
        idx = {v: i for i, v in enumerate(arr)}  # если дубль, возьмём первый индекс
        return {k: idx.get(values.get(k, 0.0), 0) / max(n - 1, 1) for k in keys}


    def _nn_to_prob_map(
        self,
        values: Dict[DocKey, float],
        keys: List[DocKey]
    ) -> Dict[DocKey, float]:
        out: Dict[DocKey, float] = {}
        for k in keys:
            v = float(values.get(k, 0.0))

            if 0.0 <= v <= 1.0:
                out[k] = v
            else:
                out[k] = 1.0 / (1.0 + math.exp(-v))  # логит → вероятность

        return out



