import re
import uuid
import unicodedata
from typing import List, Dict, Any, Optional, Final

import blingfire  # type: ignore
from loguru import logger

from src.core.utils import EnvTools


class ChunkingService:
    def __init__(self) -> None:
        self.chunk_size = int(EnvTools.required_load_env_var("CHUNK_SIZE"))
        self.chunk_overlap = int(EnvTools.required_load_env_var("CHUNK_OVERLAP"))


    def split_paragraphs(self, text: str) -> List[str]:
        return [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]


    def split_sentences(self, paragraph: str) -> List[str]:
        try:
            sents = blingfire.text_to_sentences(paragraph).splitlines()
            return [s.strip() for s in sents if s.strip()]
            
        except Exception:
            sents = re.split(r'[.!?]+', paragraph)
            return [s.strip() for s in sents if s.strip()]


    def chunk_document(
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
                if not sentence:
                    continue
                chunk_id += 1
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "doc_id": doc_id,
                    "paragraph_id": paragraph_id,
                    "chunk_id": chunk_id,
                    "text": self.normalize_text(sentence),
                    "metadata": metadata or {},
                })

        logger.info(f"Document {doc_id} chunked: {len(chunks)} chunks, {paragraph_id} paragraphs")
        return chunks


    _WS_RE: Final = re.compile(r"\s+")
    _CONTROL_RE: Final = re.compile(r"[\u0000-\u001F\u007F]")
    _ZW_RE: Final = re.compile(r"[\u200B-\u200F\u2060\uFEFF]")  # zero-width/format chars

    _ALLOWED_RE: Final = re.compile(
        r"[^A-Za-z0-9\u0400-\u04FF\s\.\,\!\?\;\:\(\)\[\]\{\}\-\+\*/=<>^%|~'\"#\\@&_±√∑∏∫∞≈≠≤≥°]"
    )

    _TRANSLATE: Final = {
        ord("“"): '"', ord("”"): '"', ord("„"): '"', ord("«"): '"', ord("»"): '"',
        ord("‘"): "'", ord("’"): "'", ord("‚"): "'",
        ord("′"): "'", ord("″"): '"', ord("‴"): "'''",
        ord("–"): "-", ord("—"): "-", ord("‒"): "-", ord("−"): "-", ord("\u2212"): "-",
        ord("\u00A0"): " ", ord("\u2007"): " ", ord("\u202F"): " ",
        ord("×"): "*", ord("·"): "*", ord("÷"): "/", ord("⁄"): "/",
        ord("…"): "...", ord("•"): "-",
    }


    def normalize_text(self, text: str) -> str:
        t = text.strip()
        if not t:
            return ""

        t = unicodedata.normalize("NFKC", t)

        t = self._CONTROL_RE.sub("", t)
        t = self._ZW_RE.sub("", t)

        t = t.translate(self._TRANSLATE)

        t = self._WS_RE.sub(" ", t)

        t = self._ALLOWED_RE.sub("", t)

        t = self._WS_RE.sub(" ", t).strip()

        return t


