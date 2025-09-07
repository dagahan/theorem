from __future__ import annotations

import io
import os
from typing import Optional

import chardet
from docx import Document
from loguru import logger
from pypdf import PdfReader


class FileTextExtractor:
    def extract(self, filename: str, content: bytes, content_type: Optional[str]) -> str:
        name = filename.lower().strip()
        if name.endswith(".pdf") or (content_type or "").startswith("application/pdf"):
            return self._from_pdf(content)
        if name.endswith(".docx") or (content_type or "") in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
            return self._from_docx(content)
        if name.endswith(".txt") or (content_type or "").startswith("text/"):
            return self._from_text(content)
        return self._from_text_or_binary(content)


    def _from_pdf(self, content: bytes) -> str:
        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t:
                parts.append(t)
        return "\n".join(parts).strip()


    def _from_docx(self, content: bytes) -> str:
        bio = io.BytesIO(content)
        doc = Document(bio)
        parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(parts).strip()


    def _from_text(self, content: bytes) -> str:
        det = chardet.detect(content)
        enc = det.get("encoding") or "utf-8"
        try:
            return content.decode(enc, errors="replace").strip()
        except Exception:
            return content.decode("utf-8", errors="replace").strip()


    def _from_text_or_binary(self, content: bytes) -> str:
        if not content:
            return ""
        printable_ratio = sum(32 <= b <= 126 or b in (9, 10, 13) for b in content[:4096]) / min(len(content), 4096)
        if printable_ratio < 0.6:
            return ""
    
        return self._from_text(content)


        