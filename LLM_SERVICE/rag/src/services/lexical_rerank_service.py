from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Dict, Final, List, Tuple

from src.services.vector_store_service import VectorStoreService
from src.services.text_normalize_service import TextNormalizeService


class BM25Scorer:
    _DEFAULT_K1: Final[float] = 1.5
    _DEFAULT_B: Final[float] = 0.75
    _DEFAULT_SCORE: Final[float] = 0.0
    _SMOOTHING_CONSTANT: Final[float] = 0.5

    def __init__(
        self,
        document_word_lists: List[List[str]],
        k1_parameter: float = _DEFAULT_K1,
        b_parameter: float = _DEFAULT_B
    ) -> None:
        self.k1_parameter: float = k1_parameter
        self.b_parameter: float = b_parameter
        self.total_documents: int = len(document_word_lists)
        self.document_lengths: List[int] = [len(document_words) for document_words in document_word_lists]
        self.average_document_length: float = sum(self.document_lengths) / max(1, self.total_documents)

        document_frequency: Counter[str] = Counter()

        for document_words in document_word_lists:
            document_frequency.update(set(document_words))

        self.inverse_document_frequency: Dict[str, float] = {}

        for word, document_freq in document_frequency.items():
            self.inverse_document_frequency[word] = math.log(
                (self.total_documents - document_freq + self._SMOOTHING_CONSTANT) / 
                (document_freq + self._SMOOTHING_CONSTANT) + 1.0
            )


    def calculate_bm25_score(
        self,
        query_words: List[str],
        document_words: List[str]
    ) -> float:
        if not query_words or not document_words:
            return self._DEFAULT_SCORE

        term_frequency: Counter[str] = Counter(document_words)
        bm25_score: float = self._DEFAULT_SCORE
        document_length: int = len(document_words)

        normalization_factor: float = self.k1_parameter * (1.0 - self.b_parameter + self.b_parameter * document_length / max(1, self.average_document_length))

        for query_word in query_words:
            if query_word not in term_frequency:
                continue

            inverse_document_freq: float = self.inverse_document_frequency.get(query_word, self._DEFAULT_SCORE)
            term_freq: int = term_frequency[query_word]
            bm25_score += inverse_document_freq * (term_freq * (self.k1_parameter + 1.0)) / (term_freq + normalization_factor)

        return bm25_score


class LexicalRerankService:
    _MAX_PARAGRAPHS_PER_DOCUMENT: Final[int] = 3
    _DEFAULT_SCORE: Final[float] = 0.0

    def __init__(self) -> None:
        self.vector_store: VectorStoreService = VectorStoreService()
        self.text_normalizer: TextNormalizeService = TextNormalizeService()


    async def rerank_documents_by_keyword_matching(
        self,
        collection_name: str,
        semantic_results: List[Dict[str, Any]],
        query_words: List[str],
        max_lexical_results: int,
        neighbor_window_size: int
    ) -> List[Dict[str, Any]]:
        if not semantic_results:
            return []

        documents_by_id: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

        for semantic_result in sorted(semantic_results, key=lambda x: -x.get("similarity_score", self._DEFAULT_SCORE)):
            document_id, paragraph_id, chunk_id = semantic_result["document_key"]
            documents_by_id[document_id].append((paragraph_id, chunk_id))

        document_contexts: List[Tuple[Tuple[str, int, int], str]] = []

        for document_id, paragraph_chunk_pairs in documents_by_id.items():
            for paragraph_id, chunk_id in paragraph_chunk_pairs[:self._MAX_PARAGRAPHS_PER_DOCUMENT]:
                window_start: int = max(1, chunk_id - neighbor_window_size)
                window_end: int = chunk_id + neighbor_window_size

                window_chunks: List[Dict[str, Any]] = await self.vector_store.get_window_by_chunk_id(collection_name, document_id, window_start, window_end)

                for chunk_data in window_chunks:
                    chunk_payload: Dict[str, Any] = chunk_data.get("payload", chunk_data)
                    document_key: Tuple[str, int, int] = (str(chunk_payload["doc_id"]), int(chunk_payload["paragraph_id"]), int(chunk_payload["chunk_id"]))
                    document_contexts.append((document_key, chunk_payload["text"]))

        if not document_contexts:
            return []

        document_word_lists: List[List[str]] = [self._extract_words_from_text(self.text_normalizer.normalize_chunk_text(text)) for _, text in document_contexts]
        bm25_scorer: BM25Scorer = BM25Scorer(document_word_lists)

        lexical_results: List[Dict[str, Any]] = []

        for (document_key, text), document_words in zip(document_contexts, document_word_lists):
            bm25_score: float = bm25_scorer.calculate_bm25_score(query_words, document_words)
            lexical_results.append({
                "document_key": document_key, 
                "scoring_method": "bm25", 
                "bm25_score": bm25_score, 
                "document_data": {
                    "doc_id": document_key[0], 
                    "paragraph_id": document_key[1], 
                    "chunk_id": document_key[2], 
                    "text": text
                }
            })

        lexical_results.sort(key=lambda result: result["bm25_score"], reverse=True)
        return lexical_results[:max_lexical_results]


    def _extract_words_from_text(
        self,
        text: str
    ) -> List[str]:
        import re
        russian_letters = "А-Яа-яЁё"
        word_pattern = re.compile(rf"[0-9A-Za-z{russian_letters}]+")
        return [word.lower() for word in word_pattern.findall(text)]


