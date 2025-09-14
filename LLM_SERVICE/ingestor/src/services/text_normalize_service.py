from __future__ import annotations

import re
import unicodedata
from typing import Dict, Any, Final

from loguru import logger
from src.core.logging import TextNormalizeLogger


class TextNormalizeService:
    def __init__(self) -> None:
        self._ELLIPS: Final[str] = "‹ELLIPSIS›"

        self._CONTROL_ZW_RE: Final = re.compile(r"[\u0000-\u001F\u007F\u200B-\u200F\u2060\uFEFF\u00AD]")
        self._HYPHEN_BREAK_RE: Final = re.compile(r"-\s*\r?\n\s*")
        self._HARD_BREAKS_RE: Final = re.compile(r"(?:\r?\n)+")
        self._WS_RE: Final = re.compile(r"\s+")
        self._MULTI_PUNCT_RE: Final = re.compile(r"([,;:!?])\1+")

        self._ALLOWED_RE: Final = re.compile(
            r"[^A-Za-z0-9\u0400-\u04FF\u0370-\u03FF\u1F00-\u1FFF\s\.\,\!\?\;\:\(\)\[\]\{\}\-\+\*/=<>^%|~'\"#\\@&_"
            r"±√∑∏∫∞≈≠≤≥°№§€$→←⇒⇔⊂⊆⊕⊗∈∉∧∨¬≡∇∂…]"
        )

        self._TRANSLATE: Final = {
            0x201C: '"', 0x201D: '"', 0x201E: '"', 0x00AB: '"', 0x00BB: '"',
            0x2018: "'", 0x2019: "'",
            0x2032: "'", 0x2033: '"',
            0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2212: "-",
            0x2026: "...",
            0x2044: "/",
        }

        self._OCR_SPACED_WORD_RE: Final = re.compile(r'\b(?:[A-Za-zА-Яа-я]\s){3,}[A-Za-zА-Яа-я]\b')
        self._OCR_SPACED_ACRONYM_RE: Final = re.compile(r'\b([A-ZА-Я])(?:\s([A-ZА-Я])){1,6}\b')
        self._COMMON_ABBR: Final = {
            "т. е.": "т.е.", "т. к.": "т.к.", "и т. д.": "и т.д.", "и т. п.": "и т.п.",
        }

    def _collapse_ocr_spacing(self, t: str) -> str:
        t = self._OCR_SPACED_WORD_RE.sub(lambda m: m.group(0).replace(" ", ""), t)
        t = self._OCR_SPACED_ACRONYM_RE.sub(lambda m: "".join(m.group(0).split()), t)
        
        toks = t.split()
        if toks and sum(1 for w in toks if len(w) == 1) / len(toks) > 0.5:
            t = re.sub(r'(?<=\w)\s+(?=\w)', '', t)
        
        for k, v in self._COMMON_ABBR.items():
            t = t.replace(k, v)
        
        t = re.sub(r'\b([а-яё])\s+([а-яё])\b', r'\1\2', t, flags=re.IGNORECASE)
        t = re.sub(r'\b([a-z])\s+([a-z])\b', r'\1\2', t, flags=re.IGNORECASE)
        
        return t

    def normalize_chunk_text(
        self,
        text: str,
        doc_id: str = "",
        metadata: Dict[str, Any] | None = None
    ) -> str:
        """Базовая нормализация для абзацев/списков/заголовков."""
        if not text:
            return ""
        
        original_length = len(text)
        t = unicodedata.normalize("NFKC", text.strip())
        if not t:
            return ""
        t = self._CONTROL_ZW_RE.sub("", t)
        t = self._HYPHEN_BREAK_RE.sub("-", t)
        t = self._HARD_BREAKS_RE.sub(" ", t)

        t = t.translate(self._TRANSLATE)
        t = self._collapse_ocr_spacing(t)

        # защитим "..."
        t = t.replace("...", self._ELLIPS)
        t = self._ALLOWED_RE.sub("", t)
        t = self._MULTI_PUNCT_RE.sub(r"\1", t)
        t = t.replace(self._ELLIPS, "...")

        t = self._WS_RE.sub(" ", t).strip()
        
        if doc_id and metadata:
            TextNormalizeLogger.log_normalization_results(
                doc_id=doc_id,
                normalized_text=t,
                metadata=metadata,
                original_length=original_length,
                normalized_length=len(t)
            )
        
        return t


    def normalize_list_item(
        self,
        text: str
    ) -> str:
        """Для списков: сохраняем лиды (-, •, 1.) и пробел после них."""
        t = self.normalize_chunk_text(text)
        # гарантируем пробел после маркера списка
        t = re.sub(r"^(\d+[\.\)]|-|•)\s*", r"\1 ", t)
        return t


    def normalize_formula(
        self,
        text: str
    ) -> str:
        """Формулы: минимальные вмешательства, не схлопывать повторные знаки."""
        if not text:
            return ""
        t = unicodedata.normalize("NFKC", text.strip())
        t = self._CONTROL_ZW_RE.sub("", t)
        # переносы строк в формуле оставляем как пробел
        t = self._HARD_BREAKS_RE.sub(" ", t)
        # не прогоняем через _ALLOWED_RE, чтобы не выпилить узкие символы
        t = t.translate(self._TRANSLATE)
        t = self._WS_RE.sub(" ", t).strip()
        return t


    def normalize_by_kind(
        self,
        kind: str,
        text: str
    ) -> str:
        if kind in ("list",):
            return self.normalize_list_item(text)
        if kind in ("formula", "code"):
            return self.normalize_formula(text)
        # heading, paragraph, answer, table_title, table_row, default
        return self.normalize_chunk_text(text)


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


    def normalize_doc_id(
        self,
        name: str,
        max_len: int = 128,
        sep: str = "_"
    ) -> str:
        if not name:
            return "doc"

        s = unicodedata.normalize("NFKC", name).strip().lower().replace("\u00ad", "")

        CYR = {
            "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh","з":"z","и":"i","й":"i",
            "к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f",
            "х":"h","ц":"c","ч":"ch","ш":"sh","щ":"shch","ъ":"","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
            "ґ":"g","є":"e","і":"i","ї":"i","ў":"u",
        }
        GRC = {
            "α":"a","β":"b","γ":"g","δ":"d","ε":"e","ζ":"z","η":"i","θ":"th","ι":"i","κ":"k","λ":"l",
            "μ":"m","ν":"n","ξ":"x","ο":"o","π":"p","ρ":"r","σ":"s","ς":"s","τ":"t","υ":"y","φ":"f",
            "χ":"ch","ψ":"ps","ω":"o",
        }

        def _tr(ch: str) -> str:
            if ch in CYR: return CYR[ch]
            if ch in GRC: return GRC[ch]
            return ch

        s = "".join(_tr(ch) for ch in s)

        # Удаляем диакритику после транслитерации
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")

        # Разрешённый алфавит + перевод остальных в разделитель
        s = re.sub(r"[^a-z0-9_\-\.]+", sep, s)

        # Схлопываем пачки разделителей/дефисов/точек в единый sep
        s = re.sub(r"[ _\-\.]{2,}", sep, s)

        # Удаляем разделители по краям
        s = s.strip(f"{sep}-.")

        # Если первый символ не буква/цифра — префиксуем
        if not re.match(r"^[a-z0-9]", s):
            s = f"d{sep}{s}"

        # Обрезка
        if len(s) > max_len:
            s = s[:max_len].rstrip(f"{sep}-.")

        return s


