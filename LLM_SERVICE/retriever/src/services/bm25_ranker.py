from __future__ import annotations

import math
import re

from collections import Counter, defaultdict
from typing import Any, Dict, Final, List, Tuple
from src.services.vector_store_service import VectorStoreService
from src.services.synonym_service import SynonymService
from src.domain.models import Candidate, DocKey


class BM25Scorer:
    EPS: Final[float] = 1e-9

    def __init__(
        self, 
        chunk_tokens_list: List[List[str]], 
        term_frequency_weight: float = 1.5, 
        document_length_weight: float = 0.75
    ) -> None:
        """
        Initialization of the BM25 scorer to calculate the relevance of texts.
        
        1. Save the parameters of the BM25 algorithm
        2. We count statistics on the collection of chunks (how many chunks, average length)
        3. Calculate the IDF (Inverse Document Frequency) for each word
        
        Args:
            chunk_tokens_list: A list of chunks, where each chunk = a list of words
            term_frequency_weight: Term frequency weight (k1 in formula BM25)
            document_length_weight: Document length weight (b in formula BM25)
        """
        self.term_frequency_weight: float = term_frequency_weight
        self.document_length_weight: float = document_length_weight
        
        self.total_chunks_count: int = len(chunk_tokens_list)
        self.chunk_lengths: List[int] = [len(chunk) for chunk in chunk_tokens_list]
        self.average_chunk_length: float = sum(self.chunk_lengths) / max(1, self.total_chunks_count)
        
        word_document_frequency: Counter[str] = Counter()
        
        for chunk_tokens in chunk_tokens_list:
            unique_words_in_chunk: set[str] = set(chunk_tokens)
            word_document_frequency.update(unique_words_in_chunk)
        
        self.inverse_document_frequency: Dict[str, float] = {}
        
        for word, chunks_containing_word in word_document_frequency.items():
            chunks_without_word: float = self.total_chunks_count - chunks_containing_word + 0.5
            chunks_with_word: float = chunks_containing_word + 0.5
            
            self.inverse_document_frequency[word] = math.log(chunks_without_word / chunks_with_word + 1.0)


    def calculate_candidate_relevance_score(
        self,
        question_tokens: List[str],
        chunk_tokens: List[str]
    ) -> float:
        """
        Calculates the relevance between the question and the chunk using the BM25 algorithm.
        
        1. Calculate the frequency of each question word in the chunk
        2. Calculate the normalization of the length of the chunk
        3. Apply the BM25 formula for each question word
        4. Let's summarize all the estimates
        
        Args:
            question_tokens: Words from a user question
            chunk_tokens: Words from the document's chunk
        """
        if not question_tokens or not chunk_tokens:
            return 0.0

        word_frequency_in_chunk: Counter[str] = Counter(chunk_tokens)
        chunk_length_in_words: int = len(chunk_tokens)
        
        length_normalization_factor: float = self.term_frequency_weight * (
            1.0 - self.document_length_weight + 
            self.document_length_weight * chunk_length_in_words / max(1, self.average_chunk_length)
        )

        total_relevance_score: float = 0.0
        
        for question_word in question_tokens:
            if question_word not in word_frequency_in_chunk:
                continue
            
            word_frequency: int = word_frequency_in_chunk[question_word]
            inverse_document_frequency: float = self.inverse_document_frequency.get(question_word, 0.0)
            
            word_relevance: float = inverse_document_frequency * (
                word_frequency * (self.term_frequency_weight + 1.0)
            ) / (word_frequency + length_normalization_factor + self.EPS)
            
            total_relevance_score += word_relevance

        return total_relevance_score


class Bm25Ranker:
    MAX_PAR_BY_DOC: Final[int] = 9


    def __init__(self) -> None:
        self.vector_store= VectorStoreService()
        self.synonym_service = SynonymService()
        self.word_re: re.Pattern[str] = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")


    async def rank_candidates_with_bm25(
        self,
        collection_name: str,
        ann_candidates: List[Candidate],
        question: str,
        neighbor_window_size: int,
        max_results: int
    ) -> List[Candidate]:
        if not ann_candidates:
            return []

        by_doc: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        for candidate in sorted(ann_candidates, key=lambda x: -x.score_ann):
            doc_id, paragraph, chunk_id = candidate.key
            by_doc[doc_id].append((paragraph, chunk_id))

        contexts: List[Tuple[DocKey, str, List[int], Dict[str, Any]]] = []

        for doc_id, pairs in by_doc.items():
            for par_id, chunk_id in pairs[:self.MAX_PAR_BY_DOC]:

                start: int = max(1, chunk_id - neighbor_window_size)
                end: int = chunk_id + neighbor_window_size

                window: List[Dict[str, Any]] = await self.vector_store.get_window_by_chunk_id(collection_name, doc_id, start, end)
                for chunk in window:
                    payload: Dict[str, Any] = chunk.get("payload", chunk)
                    key: DocKey = (str(payload["doc_id"]), int(payload["paragraph_id"]), int(payload["chunk_id"]))
                    text: str = payload.get("text", "")
                    pages: List[int] = [int(p) for p in payload.get("pages", [])]
                    contexts.append((key, text, pages, payload))

        if not contexts:
            return []

        chunk_tokens: List[List[str]] = []
        for _, text, _, _ in contexts:
            chunk_tokens.append([w.lower() for w in self.word_re.findall(text)])

        base_words: List[str] = [w.lower() for w in self.word_re.findall(question)]
        expanded: List[str] = self.synonym_service.expand_words_for_bm25(base_words)
        question_tokens: List[str] = list(dict.fromkeys(base_words + expanded))

        bm25_scorer: BM25Scorer = BM25Scorer(chunk_tokens)
        scored: List[Tuple[int, float]] = []
        for i, dt in enumerate(chunk_tokens):
            scored.append((i, bm25_scorer.calculate_candidate_relevance_score(question_tokens, dt)))
        scored.sort(key=lambda x: x[1], reverse=True)

        out: List[Candidate] = []
        for rank, (idx, score) in enumerate(scored[:max_results], start=1):
            key, text, pages, payload = contexts[idx]
            out.append(Candidate(
                key=key,
                text=text,
                pages=pages,
                payload=payload,
                score_bm25=score,
                rank_bm25=rank
            ))

        return out


