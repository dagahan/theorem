from __future__ import annotations

from typing import Any, Dict, List, Tuple, TypeAlias
from loguru import logger

from src.pydantic_schemas.retriever import RetrievalQuestion, Candidate, RetrieveResult, DocKey
from src.pydantic_schemas.retriever import FusionWeights, PipelineLimits, MmrParams
from src.services.dense_retriever_service import DenseRetrieverService
from src.services.bm25_ranker import Bm25Ranker
from src.services.neural_rerank_service import NeuralRerankService
from src.services.fusion_service import FusionService
from src.services.dedup_service import DedupService
from src.services.mmr_service import MmrService

CandidatePool: TypeAlias = Dict[DocKey, Candidate]
CandidateList: TypeAlias = List[Candidate]
JsonChunk: TypeAlias = Dict[str, Any]
JsonChunkList: TypeAlias = List[JsonChunk]


class RetrieveOrchestrator:
    def __init__(self) -> None:
        self.ann = DenseRetrieverService()
        self.bm25 = Bm25Ranker()
        self.nn = NeuralRerankService()
        self.fusion = FusionService()
        self.dedup = DedupService(keep_per_paragraph=2, near_chunk_window=2)
        self.weights = FusionWeights()
        self.limits = PipelineLimits()
        self.mmr_params = MmrParams()
        self.mmr_service = MmrService(self.mmr_params.diversity_lambda)
        self.neighbor_window_size: int = 2

    async def retrieve(
        self,
        question: str,
        collection_name: str
    ) -> RetrieveResult:
        retrieval_question = RetrievalQuestion(question=question,)

        logger.info(f"retrieving question: '{retrieval_question.question}'")

        ann_candidates: CandidateList = await self.ann.retrieve_ann_candidates(
            query_text=retrieval_question.question,
            collection_name=collection_name,
            top_k=self.limits.ann_top_k
        )

        bm25_candidates: CandidateList = await self.bm25.rank_candidates_with_bm25(
            collection_name=collection_name,
            ann_candidates=ann_candidates,
            question=retrieval_question.question,
            neighbor_window_size=self.neighbor_window_size,
            max_results=self.limits.ann_top_k
        )

        union_pool: CandidatePool = {}
        candidate_sources: Tuple[CandidateList, CandidateList] = (ann_candidates, bm25_candidates)
        
        for candidate_source in candidate_sources:
            for candidate in candidate_source:
                union_pool.setdefault(candidate.key, candidate)

        union_list: CandidateList = list(union_pool.values())
        union_list.sort(
            key=lambda candidate: (candidate.score_ann + candidate.score_bm25), 
            reverse=True
        )
        
        nn_candidates: CandidateList = await self.nn.rerank(
            question=retrieval_question.question,
            candidates=union_list,
            topn=self.limits.nn_top_k
        )

        fused_candidates: CandidateList = self.fusion.fuse(
            ann_candidates=ann_candidates,
            bm25_candidates=bm25_candidates,
            neural_rerank_candidates=nn_candidates,
            neural_rerank_weight=self.weights.nn,
            bm25_weight=self.weights.bm25,
            rrf_weight=self.weights.rrf,
            max_results=self.limits.fusion_pool_cap
        )

        deduplicated_candidates: CandidateList = self.dedup.deduplicate(fused_candidates)

        mmr_pool_size: int = min(self.mmr_params.mmr_pool_k, len(deduplicated_candidates))
        
        mmr_reordered_candidates: CandidateList = await self.mmr_service.reorder(
            question=retrieval_question.question,
            items=deduplicated_candidates,
            k=mmr_pool_size
        )

        final_top_candidates: CandidateList = mmr_reordered_candidates[:self.limits.final_top_k]
        
        results_chunks: JsonChunkList = [
            candidate.to_json() for candidate in final_top_candidates
        ]
        
        return RetrieveResult(chunks=results_chunks)

