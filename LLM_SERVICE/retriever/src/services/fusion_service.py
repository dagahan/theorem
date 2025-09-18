from __future__ import annotations
from typing import Any, Callable, Dict, Final, List, Tuple
import math
from src.domain.models import Candidate, DocKey


class FusionService:
    _RRF_K: Final[int] = 60
    _EPS: Final[float] = 1e-9


    def fuse(
        self,
        ann_candidates: List[Candidate],
        bm25_candidates: List[Candidate],
        neural_rerank_candidates: List[Candidate],
        neural_rerank_weight: float = 0.70,
        bm25_weight: float = 0.20,
        rrf_weight: float = 0.10,
        max_results: int = 300
    ) -> List[Candidate]:
        ann_ranking_map = self._create_ranking_map(
            ann_candidates,
            key_attr="rank_ann",
            fallback=lambda x: -x.score_ann
        )

        bm25_ranking_map = self._create_ranking_map(
            bm25_candidates,
            key_attr="rank_bm25",
            fallback=lambda x: -x.score_bm25
        )

        ann_score_map = {candidate.key: candidate.score_ann for candidate in ann_candidates}

        bm25_score_map = {candidate.key: candidate.score_bm25 for candidate in bm25_candidates}
        
        neural_rerank_score_map = {candidate.key: candidate.score_nn for candidate in neural_rerank_candidates}

        all_document_keys: List[DocKey] = list(self._collect_all_keys([ann_ranking_map, bm25_ranking_map, neural_rerank_score_map]))

        reciprocal_rank_fusion_scores = self._calculate_reciprocal_rank_fusion(all_document_keys, ann_ranking_map, bm25_ranking_map)

        def normalize_to_minmax_range(values: Dict[DocKey, float]) -> Dict[DocKey, float]:
            score_values = [values.get(key, 0.0) for key in all_document_keys]
            min_score, max_score = (min(score_values), max(score_values)) if score_values else (0.0, 1.0)
            if max_score - min_score < self._EPS:
                return {key: 0.0 for key in all_document_keys}
            return {key: (values.get(key, 0.0) - min_score) / (max_score - min_score) for key in all_document_keys}

        def convert_to_probability(values: Dict[DocKey, float]) -> Dict[DocKey, float]:
            probability_map: Dict[DocKey, float] = {}
            for key in all_document_keys:
                raw_value = float(values.get(key, 0.0))
                probability_map[key] = raw_value if 0.0 <= raw_value <= 1.0 else 1.0 / (1.0 + math.exp(-raw_value))
            return probability_map

        normalized_ann_scores = normalize_to_minmax_range(ann_score_map)
        normalized_bm25_scores = normalize_to_minmax_range({key: math.log1p(score) for key, score in bm25_score_map.items()})
        normalized_rrf_scores = self._convert_to_percentile_ranks(reciprocal_rank_fusion_scores, all_document_keys)
        normalized_neural_rerank_scores = convert_to_probability(neural_rerank_score_map)

        merged_candidates: Dict[DocKey, Candidate] = {}
        for candidate_source in (ann_candidates, bm25_candidates, neural_rerank_candidates):
            for candidate in candidate_source:
                merged_candidates.setdefault(candidate.key, Candidate(key=candidate.key, text=candidate.text, pages=candidate.pages, payload=candidate.payload))

        final_candidates: List[Candidate] = []
        for document_key in all_document_keys:
            candidate = merged_candidates[document_key]
            candidate.score_ann = ann_score_map.get(document_key, 0.0)
            candidate.score_bm25 = bm25_score_map.get(document_key, 0.0)
            candidate.score_nn = neural_rerank_score_map.get(document_key, 0.0)
            candidate.score_rrf = normalized_rrf_scores.get(document_key, 0.0)
            candidate.score_total = neural_rerank_weight * normalized_neural_rerank_scores.get(document_key, 0.0) + bm25_weight * normalized_bm25_scores.get(document_key, 0.0) + rrf_weight * normalized_rrf_scores.get(document_key, 0.0)
            final_candidates.append(candidate)

        final_candidates.sort(key=lambda candidate: (candidate.score_total, candidate.score_nn, candidate.score_rrf), reverse=True)
        return final_candidates[:max_results]


    def _create_ranking_map(
        self,
        candidates: List[Candidate],
        key_attr: str,
        fallback: Callable[[Candidate], float]
    ) -> Dict[DocKey, int]:
        if not candidates:
            return {}

        if any(getattr(candidate, key_attr) is not None for candidate in candidates):
            key_rank_pairs = [(candidate.key, getattr(candidate, key_attr) or 10**9) for candidate in candidates]
            key_rank_pairs.sort(key=lambda pair: pair[1])
            return {document_key: rank_position + 1 for rank_position, (document_key, _) in enumerate(key_rank_pairs)}

        sorted_candidates = sorted(candidates, key=fallback)

        return {candidate.key: rank_position + 1 for rank_position, candidate in enumerate(sorted_candidates)}


    def _collect_all_keys(
        self,
        dictionaries:
        List[Dict[DocKey, Any]]
    ) -> List[DocKey]:
        unique_keys: set[DocKey] = set()
        for dictionary in dictionaries:
            unique_keys.update(dictionary.keys())
        return list(unique_keys)


    def _calculate_reciprocal_rank_fusion(
        self,
        document_keys:
        List[DocKey],
        ann_ranking_map: Dict[DocKey, int],
        bm25_ranking_map: Dict[DocKey, int]
    ) -> Dict[DocKey, float]:
        rrf_scores: Dict[DocKey, float] = {}
        
        for document_key in document_keys:
            reciprocal_sum = 0.0
            if document_key in ann_ranking_map:
                reciprocal_sum += 1.0 / (self._RRF_K + ann_ranking_map[document_key])
            if document_key in bm25_ranking_map:
                reciprocal_sum += 1.0 / (self._RRF_K + bm25_ranking_map[document_key])
            rrf_scores[document_key] = reciprocal_sum

        return rrf_scores


    def _convert_to_percentile_ranks(
        self,
        score_values: Dict[DocKey, float],
        document_keys: List[DocKey]
    ) -> Dict[DocKey, float]:
        sorted_scores = sorted(score_values.get(key, 0.0) for key in document_keys)
        total_count = len(sorted_scores) or 1
        score_to_index_map = {score: index for index, score in enumerate(sorted_scores)}

        return {key: score_to_index_map.get(score_values.get(key, 0.0), 0) / max(total_count - 1, 1) for key in document_keys}



