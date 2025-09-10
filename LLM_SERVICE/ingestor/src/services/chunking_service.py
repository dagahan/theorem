import re
import uuid
import unicodedata
import os
import json
from typing import List, Dict, Any, Optional, Final
from datetime import datetime

import blingfire  # type: ignore
from loguru import logger

from src.core.utils import EnvTools, FileSystemTools


class ChunkingService:
    def __init__(self) -> None:
        self.chunk_size: int = int(EnvTools.required_load_env_var("CHUNK_SIZE"))
        self.chunk_overlap: int = int(EnvTools.required_load_env_var("CHUNK_OVERLAP"))


    def _log_chuncking_results(
        self,
        doc_id: str,
        filename: str,
        extracted_text: str,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        paragraph_count: int
    ) -> None:
        try:
            log_chuncking_entry = {
                "timestamp": datetime.now().isoformat(),
                "doc_id": doc_id,
                "filename": filename,
                "metadata": metadata,
                "extracted_text_length": len(extracted_text),
                "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
                "chunks_count": len(chunks),
                "chunks": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "paragraph_id": chunk["paragraph_id"],
                        "text_length": len(chunk["text"]),
                        "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
                    }
                    for chunk in chunks
                ]
            }
            
            debug_dir = "debug/chuncking"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{filename}_{doc_id}.json")
            
            with open(file_path, "a", encoding="utf-8") as file:
                file.write(json.dumps(log_chuncking_entry, indent=2, ensure_ascii=False))
                file.write("\n\n")
            
            logger.debug(f"Document {doc_id} chunked: {len(chunks)} chunks, {paragraph_count} paragraphs")
            logger.debug(f"Processing results logged to debug log file: {file_path} for doc_id: {doc_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log processing results: {ex}")


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

        filename = metadata.get("filename", "unknown") if metadata else "unknown"
        self._log_chuncking_results(doc_id, filename, text, chunks, metadata or {}, paragraph_id)

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


    def normalize_text(
        self,
        text: str
    ) -> str:
        text = text.strip()
        if not text:
            return ""

        text = unicodedata.normalize("NFKC", text)

        text = self._CONTROL_RE.sub("", text)
        text = self._ZW_RE.sub("", text)

        text = text.translate(self._TRANSLATE)

        text = self._WS_RE.sub(" ", text)

        text = self._ALLOWED_RE.sub("", text)

        text = self._WS_RE.sub(" ", text).strip()

        return text



