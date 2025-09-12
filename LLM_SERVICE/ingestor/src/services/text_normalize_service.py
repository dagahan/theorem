from __future__ import annotations

import re
import unicodedata
from typing import Dict, Any, Final

from loguru import logger
from src.core.logging import TextNormalizeLogger


class TextNormalizeService:
    def __init__(self) -> None:
        self._WS_RE: Final = re.compile(r"\s+")
        self._CONTROL_RE: Final = re.compile(r"[\u0000-\u001F\u007F]")
        self._ZW_RE: Final = re.compile(r"[\u200B-\u200F\u2060\uFEFF]")
        self._MULTI_PUNCT_RE: Final = re.compile(r"([,.;:!?])\1+")
        self._HARD_BREAKS_RE: Final = re.compile(r"(?:\r?\n)+")
        self._HYPHEN_BREAK_RE: Final = re.compile(r"-\s*\r?\n\s*")
        self._BULLET_PREFIX_RE: Final = re.compile(r"^\s*(?:[\-\u2022\u2023\u25E6\u2043\u2219•]|(\(?\d{1,3}[\).\:]))\s+")
        self._ALLOWED_RE: Final = re.compile(
            r"[^A-Za-z0-9\u0400-\u04FF\s\.\,\!\?\;\:\(\)\[\]\{\}\-\+\*/=<>^%|~'\"#\\@&_±√∑∏∫∞≈≠≤≥°]"
        )

        self._TRANSLATE: Final = {
            0x201C: '"', 0x201D: '"', 0x201E: '"', 0x00AB: '"', 0x00BB: '"',
            0x2018: "'", 0x2019: "'", 0x201A: "'",
            0x2032: "'", 0x2033: '"', 0x2034: "'''",
            0x2013: "-", 0x2014: "-", 0x2012: "-", 0x2212: "-", 0x2212: "-",
            0x00A0: " ", 0x2007: " ", 0x202F: " ",
            0x00D7: "*", 0x00B7: "*", 0x00F7: "/", 0x2044: "/",
            0x2026: "...", 0x2022: "-",
        }


    def normalize_text(
        self,
        text: str,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> str:
        try:
            original_text = text
            original_length = len(text)
            
            normalized_text = self.normalize_chunk_text(text)
            
            TextNormalizeLogger.log_normalization_results(
                doc_id=doc_id,
                normalized_text=normalized_text,
                metadata=metadata,
                original_length=original_length,
                normalized_length=len(normalized_text)
            )
            
            logger.debug(f"Text normalized for {doc_id}: {original_length} -> {len(normalized_text)} chars")
            return normalized_text
            
        except Exception as e:
            logger.error(f"Failed to normalize text for {doc_id}: {e}")
            return text


    def normalize_chunk_text(
        self,
        text: str
    ) -> str:
        if not text:
            return ""
        normalized_text = text.strip()
        if not normalized_text:
            return ""
        normalized_text = unicodedata.normalize("NFKC", normalized_text)

        normalized_text = self._CONTROL_RE.sub("", normalized_text)
        normalized_text = self._ZW_RE.sub("", normalized_text)

        normalized_text = self._HYPHEN_BREAK_RE.sub("-", normalized_text)
        normalized_text = self._HARD_BREAKS_RE.sub(" ", normalized_text)

        normalized_text = normalized_text.translate(self._TRANSLATE)

        normalized_text = self._BULLET_PREFIX_RE.sub("", normalized_text)

        normalized_text = self._ALLOWED_RE.sub("", normalized_text)

        normalized_text = self._MULTI_PUNCT_RE.sub(r"\1", normalized_text)

        normalized_text = self._WS_RE.sub(" ", normalized_text).strip()
        return normalized_text


    def normalize_identifier(
        self,
        identifier: str
    ) -> str:
        if not identifier:
            return ""
        
        normalized_id = unicodedata.normalize("NFKC", identifier).lower()
        normalized_id = re.sub(r"\s+", "_", normalized_id)
        normalized_id = re.sub(r"[^a-z0-9\u0400-\u04FF_\-\.]", "-", normalized_id).strip("-. _")
        
        return normalized_id


