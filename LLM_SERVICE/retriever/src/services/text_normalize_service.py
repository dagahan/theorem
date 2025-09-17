from __future__ import annotations

import re
import unicodedata
from typing import Final


class TextNormalizeService:
    def __init__(self) -> None:
        self._TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9_]+", re.UNICODE)
        self._CONTROL_ZW_RE: Final = re.compile(r"[\u0000-\u001F\u007F\u200B-\u200F\u2060\uFEFF\u00AD]")
        self._HYPHEN_BREAK_RE: Final = re.compile(r"-\s*\r?\n\s*")
        self._HARD_BREAKS_RE: Final = re.compile(r"(?:\r?\n)+")
        self._WS_RE: Final = re.compile(r"\s+")

        self._TRANSLATE: Final = {
            0x201C: '"', 0x201D: '"', 0x201E: '"', 0x00AB: '"', 0x00BB: '"',
            0x2018: "'", 0x2019: "'",
            0x2032: "'", 0x2033: '"',
            0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2212: "-",
            0x2026: "...",
            0x2044: "/",
        }


    def normalize_query_text(
        self,
        text: str
    ) -> str:
        if not text:
            return ""
        
        # jsut normalizing text into unicode symbols.
        text = unicodedata.normalize("NFKC", text.strip())
        if not text:
            return ""

        # removing control chars, fixing hyphens, cleaning whitespace
        text = self._CONTROL_ZW_RE.sub("", text)
        text = self._HYPHEN_BREAK_RE.sub("-", text)
        text = self._HARD_BREAKS_RE.sub(" ", text)
        text = text.translate(self._TRANSLATE)
        text = self._WS_RE.sub(" ", text).strip()
        
        return text


    def extract_words(self, text: str) -> list[str]:
        return [m.group(0).lower() for m in self._TOKEN_RE.finditer(text)]

