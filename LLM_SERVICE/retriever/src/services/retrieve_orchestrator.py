from __future__ import annotations

import time
from typing import Any, Dict, List
from loguru import logger

import asyncio

from src.pydantic_schemas.retriever import Candidate, RetrievalQuestion, RetrieveResult
from src.services.dense_retriever_service import DenseRetrieverService
from src.services.sparse_retriever_service import SparseRetrieverService
from src.services.neural_rerank_service import NeuralRerankService
from src.services.candidate_merge_service import CandidateMergeService
from src.core.logging import SearchLogger, StepLogger

CandidateList = List[Candidate]
JsonChunkList = List[Dict[str, Any]]


class RetrieveOrchestrator:
    def __init__(self) -> None:
        self.dense_retriever = DenseRetrieverService()
        self.sparse_retriever = SparseRetrieverService()
        self.nn = NeuralRerankService()
        self.merger = CandidateMergeService()
        
        self.semantic_top_k = 10
        self.lexical_top_k = 5
        self.final_top_k = 15
        self.rerank_pool_cap = 64

    async def retrieve(
        self,
        question: str,
        collection_name: str
    ) -> RetrieveResult:
        start_time = time.time()
        retrieval_question = RetrievalQuestion(question=question,)

        logger.info(f"retrieving question: '{retrieval_question.question}'")
        
        dense_task = asyncio.create_task(
            self.dense_retriever.retrieve_ann_candidates(
                query_text=retrieval_question.question,
                collection_name=collection_name,
                top_k=self.semantic_top_k
            )
        )
        
        sparse_task = asyncio.create_task(
            self.sparse_retriever.retrieve_sparse_candidates(
                query_text=retrieval_question.question,
                collection_name=collection_name,
                top_k=self.lexical_top_k
            )
        )
        
        dense_candidates, sparse_candidates = await asyncio.gather(dense_task, sparse_task)

        logger.info(f"Dense search found {len(dense_candidates)} candidates")
        logger.info(f"Sparse search found {len(sparse_candidates)} candidates")

        dense_time = time.time() - start_time
        sparse_time = time.time() - start_time

        dense_results = [candidate.to_json() for candidate in dense_candidates]
        sparse_results = [candidate.to_json() for candidate in sparse_candidates]

        StepLogger.log_search_results(
            search_type="dense",
            query=retrieval_question.question,
            collection_name=collection_name,
            candidates=dense_results,
            execution_time_ms=dense_time * 1000
        )

        StepLogger.log_search_results(
            search_type="sparse",
            query=retrieval_question.question,
            collection_name=collection_name,
            candidates=sparse_results,
            execution_time_ms=sparse_time * 1000
        )

        merged_candidates: CandidateList = self.merger.merge_and_deduplicate(
            dense_candidates, sparse_candidates
        )

        logger.info(f"After merge and deduplication: {len(merged_candidates)} candidates")

        pool = merged_candidates[:self.rerank_pool_cap]

        reranked_candidates: CandidateList = await self.nn.rerank(
            question=retrieval_question.question,
            candidates=pool,
            topn=len(pool)
        )

        reranked_candidates.sort(key=lambda x: x.score_nn, reverse=True)

        final_top_candidates: CandidateList = reranked_candidates[:self.final_top_k]
        
        results_chunks: JsonChunkList = [
            candidate.to_json() for candidate in final_top_candidates
        ]
        
        total_time_ms = (time.time() - start_time) * 1000
        
        pipeline_steps = {
            "dense_candidates_count": len(dense_candidates),
            "sparse_candidates_count": len(sparse_candidates),
            "merged_candidates_count": len(merged_candidates),
            "rerank_pool_size": len(pool),
            "final_candidates_count": len(final_top_candidates)
        }
        
        SearchLogger.log_search_pipeline(
            query=retrieval_question.question,
            collection_name=collection_name,
            pipeline_steps=pipeline_steps,
            final_results=results_chunks,
            total_time_ms=total_time_ms
        )
        
        return RetrieveResult(chunks=results_chunks)

