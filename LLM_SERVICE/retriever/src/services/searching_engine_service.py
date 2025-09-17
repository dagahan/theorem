from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Final
from loguru import logger

from src.core.utils import EnvTools
from src.core.logging import SearchLogger, StepLogger
from src.services.text_normalize_service import TextNormalizeService
from src.services.synonym_service import SynonymService
from src.services.query_analysis_service import QueryAnalysisService
from src.services.retriever_service import DenseRetrieverService
from src.services.bm25_ranker import Bm25Ranker
from src.services.fusion_service import FusionService
from src.services.context_builder_service import ContextBuilderService
from src.services.neural_rerank_service import NeuralRerankService


class SearchingEngineService:
    def __init__(self) -> None:
        self.text_normalizer = TextNormalizeService()
        self.synonym_expander = SynonymService()
        self.query_analyzer = QueryAnalysisService()
        self.retriever = DenseRetrieverService()
        self.lexical_reranker = Bm25Ranker()
        self.neural_reranker = NeuralRerankService()
        self.fusion_service = FusionService()
        self.context_builder = ContextBuilderService()

        self.top_k = int(EnvTools.required_load_env_var("TOP_K"))
        self.top_m = int(EnvTools.required_load_env_var("TOP_M"))
        self.context_window_size = int(EnvTools.required_load_env_var("CONTEXT_WINDOW_SIZE"))
        self.include_whole_paragraph = bool(EnvTools.required_load_env_var("INCLUDE_WHOLE_PARAGRAPH"))
        self.rerank_topn = int(EnvTools.required_load_env_var("RERANK_TOPN"))


    async def retrieve_context(
        self,
        query: str,
        collection_name: str,
    ) -> Dict[str, Any]:
        start_time = time.time()
        pipeline_steps = {}
        
        # Step 1: Normalize query text
        step_start = time.time()
        normalized_query = self.text_normalizer.normalize_query_text(query)
        pipeline_steps["step_1_normalize"] = {
            "input_query": query,
            "normalized_query": normalized_query,
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("normalize_query", pipeline_steps["step_1_normalize"], float(pipeline_steps["step_1_normalize"]["execution_time_ms"]))  # type: ignore

        # Step 2: Decompose complex query into semantic parts
        step_start = time.time()
        query_parts = self.query_analyzer.decompose_query_into_semantic_parts(normalized_query)
        pipeline_steps["step_2_decompose"] = {
            "query_parts": query_parts,
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("decompose_query", pipeline_steps["step_2_decompose"], float(pipeline_steps["step_2_decompose"]["execution_time_ms"]))  # type: ignore

        # Step 3: Expand query with comprehensive synonym variants
        step_start = time.time()
        expanded_queries_with_synonyms = self.synonym_expander.expand_query_variants(query_parts)
        pipeline_steps["step_3_expand"] = {
            "expanded_queries": expanded_queries_with_synonyms,
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("expand_synonyms", pipeline_steps["step_3_expand"], float(pipeline_steps["step_3_expand"]["execution_time_ms"]))  # type: ignore

        # Step 4: Extract individual words for lexical matching
        step_start = time.time()
        unique_query_words = self.query_analyzer.extract_unique_searchable_words(normalized_query)
        pipeline_steps["step_4_extract_words"] = {
            "query_words": unique_query_words,
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("extract_words", pipeline_steps["step_4_extract_words"], float(pipeline_steps["step_4_extract_words"]["execution_time_ms"]))  # type: ignore

        # Step 5: Total dense retrieval using semantic embeddings
        step_start = time.time()
        semantic_results = await self._execute_total_semantic_search(
            expanded_queries_with_synonyms,
            collection_name
        )
        pipeline_steps["step_5_semantic"] = {
            "results_count": len(semantic_results),
            "top_scores": [r.get("similarity_score", 0.0) for r in semantic_results[:5]],
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("semantic_search", pipeline_steps["step_5_semantic"], float(pipeline_steps["step_5_semantic"]["execution_time_ms"]))  # type: ignore

        # Step 6: Neural reranking with cross-encoder
        step_start = time.time()
        neural_results = await self.neural_reranker.neural_rerank(
            normalized_query, semantic_results, self.rerank_topn
        )
        pipeline_steps["step_6_neural_rerank"] = {
            "results_count": len(neural_results),
            "top_neural_scores": [r.get("neural_score", 0.0) for r in neural_results[:5]],
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("neural_rerank", pipeline_steps["step_6_neural_rerank"], float(pipeline_steps["step_6_neural_rerank"]["execution_time_ms"]))  # type: ignore

        # Step 7: Lexical reranking with BM25 algorithm
        step_start = time.time()
        lexical_results = await self.lexical_reranker.rerank_documents_by_keyword_matching(
            collection_name,
            semantic_results,
            unique_query_words,
            self.top_k,
            self.context_window_size
        )
        pipeline_steps["step_7_lexical_rerank"] = {
            "results_count": len(lexical_results),
            "top_bm25_scores": [r.get("bm25_score", 0.0) for r in lexical_results[:5]],
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("lexical_rerank", pipeline_steps["step_7_lexical_rerank"], float(pipeline_steps["step_7_lexical_rerank"]["execution_time_ms"]))  # type: ignore

        # Step 8: Fusion of dense, neural and lexical scoring methods
        step_start = time.time()
        fused_results = self.fusion_service.fuse(
            ann=semantic_results,
            bm25=lexical_results,
            nn=neural_results,
            max_results=self.top_k
        )
        pipeline_steps["step_8_fusion"] = {
            "results_count": len(fused_results),
            "top_combined_scores": [r.get("score", 0.0) for r in fused_results[:5]],
            "weights": {
                "nn": 0.70,
                "bm25": 0.20,
                "rrf": 0.10
            },
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("fusion", pipeline_steps["step_8_fusion"], float(pipeline_steps["step_8_fusion"]["execution_time_ms"]))  # type: ignore

        # Step 9: Build context windows around each result
        step_start = time.time()
        context_windows = await self.context_builder.build_context_windows(
            collection_name=collection_name,
            ranked_documents=fused_results,
            neighbor_window_size=self.context_window_size,
            include_whole_paragraph=self.include_whole_paragraph,
            max_results=self.top_m
        )
        pipeline_steps["step_9_context_build"] = {
            "context_windows_count": len(context_windows),
            "execution_time_ms": (time.time() - step_start) * 1000
        }
        StepLogger.log_step("context_build", pipeline_steps["step_9_context_build"], float(pipeline_steps["step_9_context_build"]["execution_time_ms"]))  # type: ignore
        
        # Step 10: Apply final results limit
        context_windows = context_windows[:self.top_m]

        # Step 11: Log search diagnostics
        self._log_search_diagnostics(query, context_windows)

        # Step 12: Log complete pipeline
        total_time_ms = (time.time() - start_time) * 1000
        SearchLogger.log_search_pipeline(query, collection_name, pipeline_steps, context_windows, total_time_ms)

        # Step 13: Return context windows as structured snippets
        return {"context_windows": context_windows}

    def _log_search_diagnostics(self, query: str, context_windows: List[Dict[str, Any]]) -> None:
        if not context_windows:
            logger.warning(f"No context found for query: '{query}'")
            return
            
        # Count parent types
        parent_type_counts: Dict[str, int] = {}
        quality_scores: List[float] = []
        
        for window in context_windows:
            parent_types = window.get("parent_types", [])
            for pt in parent_types:
                parent_type_counts[pt] = parent_type_counts.get(pt, 0) + 1
                
            # Estimate quality from text
            text = window.get("context_text", "")
            alpha_count = sum(1 for ch in text if ch.isalpha())
            alpha_ratio = alpha_count / max(1, len(text))
            quality_scores.append(alpha_ratio)
            
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        logger.info(f"Search diagnostics for '{query[:50]}...': "
                   f"results={len(context_windows)}, "
                   f"avg_quality={avg_quality:.3f}, "
                   f"parent_types={parent_type_counts}")

    async def _execute_total_semantic_search(
        self,
        expanded_queries: List[str],
        collection_name: str
    ) -> List[Dict[str, Any]]:
        """Execute total semantic search with maximum Qdrant queries."""
        total_results = []
        
        for query_text in expanded_queries:
            results = await self.retriever.retrieve_documents_by_semantic_similarity(
                [query_text],
                collection_name,
                self.top_k
            )
            total_results.extend(results)
        
        return self._deduplicate_and_rank_results(total_results)

    def _deduplicate_and_rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and rank by best scores."""
        unique_results = {}
        
        for result in results:
            document_key = result["document_key"]
            if document_key not in unique_results:
                unique_results[document_key] = result
            else:
                existing_score = unique_results[document_key]["similarity_score"]
                current_score = result["similarity_score"]
                if current_score > existing_score:
                    unique_results[document_key] = result
        
        return sorted(unique_results.values(), key=lambda x: x["similarity_score"], reverse=True)


