from __future__ import annotations
from typing import Any, Dict, List, Tuple
from loguru import logger
from src.domain.models import RetrievalQuery, Candidate, RetrieveResult
from src.domain.params import FusionWeights, PipelineLimits, MmrParams
from src.services.text_normalize_service import TextNormalizeService
from src.services.dense_retriever_service import DenseRetrieverService
from src.services.bm25_ranker import Bm25Ranker
from src.services.neural_rerank_service import NeuralRerankService
from src.services.fusion_service import FusionService
from src.services.dedup_service import DedupService
from src.services.mmr_service import MmrService


class RetrieveOrchestrator:
    def __init__(self) -> None:
        self.norm = TextNormalizeService()
        self.ann = DenseRetrieverService()
        self.bm25 = Bm25Ranker()
        self.nn = NeuralRerankService()
        self.fusion = FusionService()
        self.dedup = DedupService(keep_per_paragraph=2, near_chunk_window=2)

        self.weights = FusionWeights()
        self.limits = PipelineLimits()
        self.mmr_params = MmrParams()

        self.neighbor_window_size = 2


    async def retrieve(
        self,
        query: str,
        collection_name: str
    ) -> RetrieveResult:
        retrieval_query = RetrievalQuery(
            original_text=query,
            normalized_text=self.norm.normalize_query_text(query)
        )

        logger.info(f"query: '{retrieval_query.original_text}' -> '{retrieval_query.normalized_text}'")

        ann_candidates: List[Candidate] = await self.ann.retrieve_ann_candidates(
            query_text=retrieval_query.normalized_text,
            collection_name=collection_name,
            top_k=self.limits.ann_top_k
        )

        bm25_candidates: List[Candidate] = await self.bm25.rerank_with_bm25(
            collection_name=collection_name,
            ann_candidates=ann_candidates,
            original_query=retrieval_query.original_text,
            neighbor_window_size=self.neighbor_window_size,
            max_results=self.limits.ann_top_k
        )

        union_pool: Dict[Tuple[str, int, int], Candidate] = {}
        for candidate_source in (ann_candidates, bm25_candidates):
            for candidate in candidate_source:
                union_pool.setdefault(candidate.key, candidate)

        union_list: List[Candidate] = list(union_pool.values())
        union_list.sort(key=lambda candidate: (candidate.score_ann + candidate.score_bm25), reverse=True)
        nn_candidates: List[Candidate] = await self.nn.rerank(
            query_text=retrieval_query.normalized_text,
            candidates=union_list,
            topn=self.limits.nn_top_k
        )

        fused_candidates: List[Candidate] = self.fusion.fuse(
            ann_candidates=ann_candidates,
            bm25_candidates=bm25_candidates,
            neural_rerank_candidates=nn_candidates,
            neural_rerank_weight=self.weights.nn,
            bm25_weight=self.weights.bm25,
            rrf_weight=self.weights.rrf,
            max_results=self.limits.fusion_pool_cap
        )

        deduplicated_candidates: List[Candidate] = self.dedup.deduplicate(fused_candidates)

        mmr_reordered_candidates: List[Candidate] = await MmrService(self.mmr_params.diversity_lambda).reorder(
            query_text=retrieval_query.normalized_text,
            items=deduplicated_candidates,
            k=min(self.mmr_params.mmr_pool_k, len(deduplicated_candidates))
        )

        final_top_candidates: List[Candidate] = mmr_reordered_candidates[: self.limits.final_top_k]
        
        results_chunks: List[Dict[str, Any]] = [candidate.to_json() for candidate in final_top_candidates]
        
        return RetrieveResult(chunks=results_chunks)



