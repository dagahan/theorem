from __future__ import annotations

import re
from typing import Any, Dict, List, Final

from src.core.utils import EnvTools
from src.services.text_normalize_service import TextNormalizeService
from src.services.synonym_service import SynonymService
from src.services.query_analysis_service import QueryAnalysisService
from src.services.dense_retriever_service import DenseRetrieverService
from src.services.lexical_rerank_service import LexicalRerankService
from src.services.fusion_service import FusionService
from src.services.context_builder_service import ContextBuilderService


class SearchingEngineService:
    def __init__(self) -> None:
        self.text_normalizer = TextNormalizeService()
        self.synonym_expander = SynonymService()
        self.query_analyzer = QueryAnalysisService()
        self.dense_retriever = DenseRetrieverService()
        self.lexical_reranker = LexicalRerankService()
        self.fusion_service = FusionService()
        self.context_builder = ContextBuilderService()

        self.top_k = int(EnvTools.required_load_env_var("TOP_K"))
        self.top_m = int(EnvTools.required_load_env_var("TOP_M"))
        self.context_window_size = int(EnvTools.required_load_env_var("CONTEXT_WINDOW_SIZE"))
        self.include_whole_paragraph = bool(EnvTools.required_load_env_var("INCLUDE_WHOLE_PARAGRAPH"))
        self.rrf_weight = float(EnvTools.required_load_env_var("WEIGHT_RRF"))
        self.bm25_weight = float(EnvTools.required_load_env_var("WEIGHT_BM25"))
        self.semantic_weight = float(EnvTools.required_load_env_var("WEIGHT_SEMANTIC"))


    async def retrieve_context(
        self,
        query: str,
        collection_name: str,
    ) -> Dict[str, Any]:
        # Step 1: Normalize query text
        normalized_query = self.text_normalizer.normalize_chunk_text(query)

        # Step 2: Decompose complex query into semantic parts
        query_parts = self.query_analyzer.decompose_query_into_semantic_parts(normalized_query)

        # Step 3: Expand query with comprehensive synonym variants
        expanded_queries = self.synonym_expander.expand_query_variants(query_parts)

        # Step 4: Extract individual words for lexical matching
        query_words = self.query_analyzer.extract_searchable_words(normalized_query)

        # Step 5: Dense retrieval using semantic embeddings
        semantic_results = await self.dense_retriever.retrieve_documents_by_semantic_similarity(
            expanded_queries,
            collection_name,
            self.top_k
        )

        # Step 6: Lexical reranking with BM25 algorithm
        lexical_results = await self.lexical_reranker.rerank_documents_by_keyword_matching(
            collection_name,
            semantic_results,
            query_words,
            self.top_k,
            self.context_window_size
        )

        # Step 7: Fusion of dense and lexical scoring methods
        fused_results = self.fusion_service.combine_semantic_and_lexical_scores(
            semantic_results,
            lexical_results,
            max_results=self.top_k,
            reciprocal_rank_fusion_weight=self.rrf_weight,
            bm25_weight=self.bm25_weight,
            semantic_similarity_weight=self.semantic_weight
        )

        # Step 8: Build context windows around each result
        context_windows = await self.context_builder.build_context_windows(
            collection_name=collection_name,
            ranked_documents=fused_results,
            neighbor_window_size=self.context_window_size,
            include_whole_paragraph=self.include_whole_paragraph,
            max_results=self.top_m
        )
        
        # Step 9: Apply final results limit
        context_windows = context_windows[:self.top_m]

        # Step 10: Return context windows as structured snippets
        return {"context_windows": context_windows}


