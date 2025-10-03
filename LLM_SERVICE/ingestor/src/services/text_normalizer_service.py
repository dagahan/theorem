from __future__ import annotations

import re
import unicodedata


class TextNormalizerService:
    def __init__(self) -> None:
        pass


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
        doc_id: str,
        max_len: int = 128,
        sep: str = "_"
    ) -> str:
        if not doc_id:
            return "doc"

        normalized_doc_id = unicodedata.normalize("NFKC", doc_id).strip().lower().replace("\u00ad", "")

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

        normalized_doc_id = "".join(_tr(ch) for ch in normalized_doc_id)

        normalized_doc_id = unicodedata.normalize("NFKD", normalized_doc_id)
        normalized_doc_id = "".join(c for c in normalized_doc_id if unicodedata.category(c) != "Mn")

        normalized_doc_id = re.sub(r"[^a-z0-9_\-\.]+", sep, normalized_doc_id)

        normalized_doc_id = re.sub(r"[ _\-\.]{2,}", sep, normalized_doc_id)

        normalized_doc_id = normalized_doc_id.strip(f"{sep}-.")

        if not re.match(r"^[a-z0-9]", normalized_doc_id):
            normalized_doc_id = f"d{sep}{normalized_doc_id}"

        if len(normalized_doc_id) > max_len:
            normalized_doc_id = normalized_doc_id[:max_len].rstrip(f"{sep}-.")

        return normalized_doc_id


