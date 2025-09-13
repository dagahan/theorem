from __future__ import annotations

import os
from typing import Any, Dict

from src.services.text_normalize_service import TextNormalizeService


class IdService:
    @staticmethod
    def from_filename(meta: Dict[str, Any]) -> str:
        name = str(meta.get("filename", "")).strip()
        stem = os.path.splitext(os.path.basename(name))[0]
        if not stem:
            raise ValueError("Cannot determine doc_id from filename.")

        normalized_id = TextNormalizeService().normalize_doc_id(stem)
        if not normalized_id:
            raise ValueError("Empty doc_id after filename normalization.")

        return normalized_id


    @staticmethod
    def generate_s3_key(
        collection_name: str,
        doc_id: str
    ) -> str:
        return f"{collection_name}/{doc_id}"

