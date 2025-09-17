from __future__ import annotations
import re
from typing import Final


class TextNormalizeService:
    def __init__(self) -> None:
        self._whitespace_pattern: Final[re.Pattern[str]] = re.compile(r'\s+')
        self._punctuation_pattern: Final[re.Pattern[str]] = re.compile(r'[^\w\s\u0400-\u04FF]')
    

    def normalize_query_text(self, text: str) -> str:
        if not text:
            return ""
        
        normalized = text.strip()
        normalized = self._whitespace_pattern.sub(' ', normalized)
        normalized = self._punctuation_pattern.sub('', normalized)
        normalized = normalized.lower()
        
        return normalized


        