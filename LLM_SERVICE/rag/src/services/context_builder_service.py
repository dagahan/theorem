from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, Final, List, Tuple

from src.services.vector_store_service import VectorStoreService
from src.services.text_normalize_service import TextNormalizeService


class ContextBuilderService:
    NO_CONTEXT_MESSAGE: Final[str] = "Context not found. Please refine your query or select a different collection."
    DOCUMENT_PREFIX: Final[str] = "[DOC="
    PARAGRAPH_PREFIX: Final[str] = "[PAR="
    SEPARATOR: Final[str] = "---"

    def __init__(self) -> None:
        self.vector_store: VectorStoreService = VectorStoreService()
        self.text_normalizer: TextNormalizeService = TextNormalizeService()

    def trim_to_sentences(self, text: str, max_length: int = 1200) -> str:
        if len(text) <= max_length:
            return text
        sentences = re.split(r'(?<=[\.\!\?])\s+', text)
        result_sentences = []
        current_length = 0
        for sentence in sentences:
            if not sentence: 
                continue
            if current_length + len(sentence) > max_length: 
                break
            result_sentences.append(sentence)
            current_length += len(sentence) + 1
        return (" ".join(result_sentences)).strip() + " …"

    def limit_results_per_document(self, context_windows: List[Dict[str, Any]], max_total: int, max_per_document: int = 2) -> List[Dict[str, Any]]:
        documents_windows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for window in sorted(context_windows, key=lambda w: w["relevance_score"], reverse=True):
            if len(documents_windows[window["doc_id"]]) < max_per_document:
                documents_windows[window["doc_id"]].append(window)
        all_results = []
        for document_windows in documents_windows.values():
            all_results.extend(document_windows)
        return sorted(all_results, key=lambda w: w["relevance_score"], reverse=True)[:max_total]

    async def build_context_windows(
        self,
        collection_name: str,
        ranked_documents: List[Dict[str, Any]],
        neighbor_window_size: int,
        include_whole_paragraph: bool,
        max_results: int
    ) -> List[Dict[str, Any]]:
        context_windows = []
        processed_paragraphs: set[Tuple[str, int]] = set()
        processed_windows: set[Tuple[str, int, int, int]] = set()

        for document_item in ranked_documents[:max_results]:
            document_id = str(document_item["document_data"]["doc_id"])
            paragraph_id = int(document_item["document_data"]["paragraph_id"])
            chunk_id = int(document_item["document_data"]["chunk_id"])

            if include_whole_paragraph:
                paragraph_chunks = await self.vector_store.get_paragraph_chunks(collection_name, document_id, paragraph_id)
                normalized_texts = []
                page_numbers = set()
                for chunk in paragraph_chunks:
                    payload = chunk.get("payload", chunk)
                    normalized_text = self.text_normalizer.normalize_chunk_text(payload.get("text",""))
                    if normalized_text:
                        normalized_texts.append(normalized_text)
                    for page in payload.get("pages", []):
                        page_numbers.add(int(page))
                
                paragraph_key = (document_id, paragraph_id)
                if paragraph_key in processed_paragraphs:
                    continue

                processed_paragraphs.add(paragraph_key)
                context_windows.append({
                    "doc_id": document_id,
                    "paragraph_id": paragraph_id,
                    "chunk_id": chunk_id,
                    "pages": sorted(page_numbers),
                    "text_range": f"paragraph:{paragraph_id}",
                    "context_text": self.trim_to_sentences(" ".join(normalized_texts)),
                    "relevance_score": document_item["combined_score"],
                })

            else:
                window_start = max(1, chunk_id - neighbor_window_size)
                window_end = chunk_id + neighbor_window_size
                window_chunks = await self.vector_store.get_window_by_chunk_id(collection_name, document_id, window_start, window_end)
                normalized_texts = []
                page_numbers = set()
                for chunk in window_chunks:
                    payload = chunk.get("payload", chunk)
                    normalized_text = self.text_normalizer.normalize_chunk_text(payload.get("text",""))
                    if normalized_text:
                        normalized_texts.append(normalized_text)
                    for page in payload.get("pages", []):
                        page_numbers.add(int(page))
                
                window_key = (document_id, paragraph_id, window_start, window_end)
                if window_key in processed_windows:
                    continue

                processed_windows.add(window_key)
                context_windows.append({
                    "doc_id": document_id,
                    "paragraph_id": paragraph_id,
                    "chunk_id": chunk_id,
                    "pages": sorted(page_numbers),
                    "text_range": f"chunks:{window_start}-{window_end}",
                    "context_text": self.trim_to_sentences(" ".join(normalized_texts)),
                    "relevance_score": document_item["combined_score"],
                })

        context_windows = self.limit_results_per_document(context_windows, max_results, max_per_document=2)
        return context_windows


    def assemble_context_text(
        self,
        context_windows: List[Dict[str, Any]]
    ) -> str:
        if not context_windows:
            return self.NO_CONTEXT_MESSAGE
            
        documents_by_id = defaultdict(list)

        valid_windows = [window for window in context_windows if (window.get("context_text") or "").strip()]
        if not valid_windows:
            return self.NO_CONTEXT_MESSAGE

        for window in valid_windows:
            documents_by_id[window["document_id"]].append(window)

        for document_id in documents_by_id:
            documents_by_id[document_id].sort(key=lambda window: window["relevance_score"], reverse=True)

        context_parts = []

        for document_id, document_windows in documents_by_id.items():
            context_parts.append(f"{self.DOCUMENT_PREFIX}{document_id}]")

            for window in document_windows:
                context_parts.append(f"{self.PARAGRAPH_PREFIX}{window['paragraph_id']}|SPAN={window['text_range']}]")
                context_parts.append(window["context_text"])
                context_parts.append(self.SEPARATOR)

        return "\n".join(context_parts).strip()

