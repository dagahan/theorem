import re
import uuid
import unicodedata
from typing import List, Dict, Any, Optional, Final

import blingfire  # type: ignore
from loguru import logger

from src.core.utils import EnvTools
from src.core.logging import ChunkingLogger


class ChunkingService:
    def __init__(self) -> None:
        self.chunk_size: int = int(EnvTools.required_load_env_var("CHUNK_SIZE"))
        self.chunk_overlap: int = int(EnvTools.required_load_env_var("CHUNK_OVERLAP"))


    def split_paragraphs(
        self,
        text: str
    ) -> List[str]:
        return [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]


    def split_sentences(
        self,
        paragraph: str
    ) -> List[str]:
        try:
            sents = blingfire.text_to_sentences(paragraph).splitlines()
            return [s.strip() for s in sents if s.strip()]
            
        except Exception:
            sents = re.split(r'[.!?]+', paragraph)
            return [s.strip() for s in sents if s.strip()]


    def _valid_after_norm(
        self,
        string: str
    ) -> bool:
        if not string or len(string) < 10 or len(string) > 8192:
            return False

        words = string.split()
        if len(words) < 5:
            return False
        letters = sum(ch.isalpha() for ch in string)
        if letters / max(1, len(string)) < 0.35:
            return False

        noise = sum(not (ch.isalnum() or ch.isspace()) for ch in string)
        if noise / len(string) > 0.6:
            return False
        return True


    def chunk_text(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        paragraph_id = 0
        chunk_id = 0

        for paragraph in self.split_paragraphs(text):
            paragraph_id += 1
            for sentence in self.split_sentences(paragraph):
                if not self._valid_after_norm(sentence):
                    continue
                chunk_id += 1
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "paragraph_id": paragraph_id,
                    "chunk_id": chunk_id,
                    "text": sentence,
                })

        ChunkingLogger.log_chunking_results(doc_id, text, chunks, metadata or {}, paragraph_id)
        return chunks



