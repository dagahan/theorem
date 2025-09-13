from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Final, List, Tuple


class FusionService:
    _RRF_CONSTANT: Final[int] = 60
    _DEFAULT_RANK: Final[int] = 10**9
    _DEFAULT_SCORE: Final[float] = 0.0
    _DEFAULT_MIN_SCORE: Final[float] = 0.0
    _DEFAULT_MAX_SCORE: Final[float] = 1.0

    def combine_semantic_and_lexical_scores(
        self,
        semantic_results: List[Dict[str, Any]],
        lexical_results: List[Dict[str, Any]],
        max_results: int,
        reciprocal_rank_fusion_weight: float,
        bm25_weight: float,
        semantic_similarity_weight: float,
    ) -> List[Dict[str, Any]]:
        reciprocal_rank_scores: Dict[Tuple[str, int, int], float] = defaultdict(float)

        for semantic_result in sorted(semantic_results, key=lambda x: x.get("rank_position", self._DEFAULT_RANK)):
            rank_position: int = semantic_result.get("rank_position", self._DEFAULT_RANK)
            document_key: Tuple[str, int, int] = semantic_result["document_key"]
            reciprocal_rank_scores[document_key] += 1.0 / (self._RRF_CONSTANT + rank_position)

        for rank_position, lexical_result in enumerate(sorted(lexical_results, key=lambda x: -x.get("bm25_score", self._DEFAULT_SCORE)), start=1):
            lexical_document_key: Tuple[str, int, int] = lexical_result["document_key"]
            reciprocal_rank_scores[lexical_document_key] += 1.0 / (self._RRF_CONSTANT + rank_position)

        score_components: Dict[Tuple[str, int, int], Dict[str, float]] = defaultdict(lambda: {"semantic": self._DEFAULT_SCORE, "lexical": self._DEFAULT_SCORE, "reciprocal_rank": self._DEFAULT_SCORE})
        
        for semantic_result in semantic_results:
            semantic_document_key: Tuple[str, int, int] = semantic_result["document_key"]
            score_components[semantic_document_key]["semantic"] = max(score_components[semantic_document_key]["semantic"], float(semantic_result.get("similarity_score", self._DEFAULT_SCORE)))

        for lexical_result in lexical_results:
            lexical_score_key: Tuple[str, int, int] = lexical_result["document_key"]
            score_components[lexical_score_key]["lexical"] = max(score_components[lexical_score_key]["lexical"], float(lexical_result.get("bm25_score", self._DEFAULT_SCORE)))

        for document_key, reciprocal_rank_score in reciprocal_rank_scores.items():
            score_components[document_key]["reciprocal_rank"] = reciprocal_rank_score

        semantic_scores: List[float] = [components["semantic"] for components in score_components.values()]
        lexical_scores: List[float] = [components["lexical"] for components in score_components.values()]
        reciprocal_rank_scores_list: List[float] = [components["reciprocal_rank"] for components in score_components.values()]
        
        semantic_min, semantic_max = (min(semantic_scores, default=self._DEFAULT_MIN_SCORE), max(semantic_scores, default=self._DEFAULT_MAX_SCORE))
        lexical_min, lexical_max = (min(lexical_scores, default=self._DEFAULT_MIN_SCORE), max(lexical_scores, default=self._DEFAULT_MAX_SCORE))
        reciprocal_rank_min, reciprocal_rank_max = (min(reciprocal_rank_scores_list, default=self._DEFAULT_MIN_SCORE), max(reciprocal_rank_scores_list, default=self._DEFAULT_MAX_SCORE))

        def normalize_score(score: float, min_score: float, max_score: float) -> float:
            return (score - min_score) / (max_score - min_score) if max_score > min_score else self._DEFAULT_SCORE

        combined_results: List[Tuple[Tuple[str, int, int], float]] = []
        for document_key, score_components_dict in score_components.items():
            normalized_semantic: float = normalize_score(score_components_dict.get("semantic", self._DEFAULT_SCORE), semantic_min, semantic_max)
            normalized_lexical: float = normalize_score(score_components_dict.get("lexical", self._DEFAULT_SCORE), lexical_min, lexical_max)
            normalized_reciprocal_rank: float = normalize_score(score_components_dict.get("reciprocal_rank", self._DEFAULT_SCORE), reciprocal_rank_min, reciprocal_rank_max)
            
            combined_score: float = (reciprocal_rank_fusion_weight * normalized_reciprocal_rank + 
                                    bm25_weight * normalized_lexical + 
                                    semantic_similarity_weight * normalized_semantic)
            combined_results.append((document_key, combined_score))
            
        combined_results.sort(key=lambda result: result[1], reverse=True)

        document_lookup: Dict[Tuple[str, int, int], Dict[str, Any]] = {}

        for semantic_result in semantic_results:
            document_lookup[semantic_result["document_key"]] = semantic_result["document_data"]

        for lexical_result in lexical_results:
            lexical_lookup_key: Tuple[str, int, int] = lexical_result["document_key"]
            document_lookup[lexical_lookup_key] = document_lookup.get(lexical_lookup_key, lexical_result["document_data"]) or lexical_result["document_data"]

        final_results: List[Dict[str, Any]] = [
            {
                "document_key": document_key, 
                "document_data": document_lookup[document_key], 
                "combined_score": combined_score
            } 
            for document_key, combined_score in combined_results 
            if document_key in document_lookup
        ][:max_results]

        return final_results
