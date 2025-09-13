from __future__ import annotations

import re
from typing import Final, List, Set

from src.services.text_normalize_service import TextNormalizeService


class QueryAnalysisService:
    _WORD_BOUNDARY_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-zА-Яа-я0-9_]+", re.UNICODE)
    _CONJUNCTION_PATTERN: Final[re.Pattern[str]] = re.compile(
        r"\b(?:и|а\s+также|или|where|and|or|плюс|также|кроме|кроме\s+того)\b", 
        re.IGNORECASE
    )
    _QUERY_DECOMPOSITION_THRESHOLD: Final[int] = 120
    _MIN_QUERY_PART_LENGTH: Final[int] = 3


    def __init__(self) -> None:
        self.text_normalizer: TextNormalizeService = TextNormalizeService()


    def decompose_query_into_semantic_parts(
        self,
        query: str
    ) -> List[str]:
        # Short queries don't need decomposition
        # Input: "математика" -> Output: ["математика"]
        if len(query) <= self._QUERY_DECOMPOSITION_THRESHOLD:
            return [query]

        # Split on conjunctions to separate semantic concepts
        # Input: "решение уравнений и неравенств" -> Output: ["решение уравнений", "неравенств"]
        query_parts: List[str] = self._CONJUNCTION_PATTERN.split(query)

        # Normalize each part and filter empty/short ones
        # Input: ["решение уравнений", "", "неравенств"] -> Output: ["решение уравнений", "неравенств"]
        semantic_parts: List[str] = []
        for part in query_parts:
            normalized_part: str = self.text_normalizer.normalize_chunk_text(part)
            if len(normalized_part) >= self._MIN_QUERY_PART_LENGTH:
                semantic_parts.append(normalized_part)

        # Fallback to original query if decomposition failed
        return semantic_parts if semantic_parts else [query]


    def extract_searchable_words(
        self,
        text: str
    ) -> List[str]:
        # Extract word tokens for lexical search
        # Input: "решение квадратных уравнений" -> Output: ["решение", "квадратных", "уравнений"]
        # Matches alphanumeric sequences, converts to lowercase for BM25
        words: List[str] = [match.group(0).lower() for match in self._WORD_BOUNDARY_PATTERN.finditer(text)]
        return words

    def extract_unique_searchable_words(
        self,
        text: str
    ) -> List[str]:
        # Extract unique word tokens preserving order
        # Input: "математика математика алгебра" -> Output: ["математика", "алгебра"]
        words: List[str] = self.extract_searchable_words(text)
        unique_words: Set[str] = set()
        unique_words_ordered: List[str] = []
        
        for word in words:
            if word not in unique_words:
                unique_words.add(word)
                unique_words_ordered.append(word)
        
        return unique_words_ordered


    def analyze_query_complexity(
        self,
        query: str
    ) -> dict[str, int]:
        # Analyze query characteristics for search optimization
        # Input: "решение квадратных уравнений и неравенств" -> Output: {"words": 5, "parts": 2, "conjunctions": 1}
        words: List[str] = self.extract_searchable_words(query)
        parts: List[str] = self.decompose_query_into_semantic_parts(query)
        conjunctions: int = len(self._CONJUNCTION_PATTERN.findall(query))
        
        return {
            "word_count": len(words),
            "semantic_parts_count": len(parts),
            "conjunction_count": conjunctions,
            "query_length": len(query)
        }


        