# chunking_service.py
from __future__ import annotations

import re
import uuid
from typing import List, Dict, Any, Iterable

import blingfire  # type: ignore
from loguru import logger
import statistics as st
import hashlib

from .data_classes import Block, Chunk
from .text_normalize_service import TextNormalizeService
from src.core.utils import EnvTools
from src.core.logging import ChunkingLogger


class ChunkingService:
    def __init__(self) -> None:
        self.chunk_size: int = int(EnvTools.required_load_env_var("CHUNK_SIZE"))
        self.chunk_overlap: int = int(EnvTools.required_load_env_var("CHUNK_OVERLAP"))
        self.normalizer = TextNormalizeService()


    @staticmethod
    def _split_sentences(paragraph: str) -> List[str]:
        try:
            return [s.strip() for s in blingfire.text_to_sentences(paragraph).splitlines() if s.strip()]
        except Exception:
            return [t.strip() for t in re.split(r'(?<=[.!?])\s+', paragraph) if t.strip()]


    @staticmethod
    def _valid_after_norm(
        string: str,
        *,
        allow_short: bool = False,
        is_formula: bool = False
    ) -> bool:
        if not string:
            return False

        if not allow_short and (len(string) < 10 or len(string) > 8192):
            return False

        if is_formula:
            return True

        words = string.split()
        if not allow_short and len(words) < 5:
            return False

        letters = sum(ch.isalpha() for ch in string)
        if letters / max(1, len(string)) < 0.35:
            return False

        noise = sum(not (ch.isalnum() or ch.isspace()) for ch in string)
        if noise / len(string) > 0.6:
            return False

        return True


    @staticmethod
    def _est_tokens(s: str) -> int:
        return int(len(blingfire.text_to_words(s).split()) * 1.25 + 0.5)


    @staticmethod
    def _p95(values: List[int]) -> int:
        if not values:
            return 0
        k = max(0, int(0.95 * len(values)) - 1)
        return sorted(values)[k]


    def _calc_targets(
        self,
        sent_token_lengths: List[int]
    ) -> Dict[str, int]:
        if not sent_token_lengths:
            return {"T_min": 200, "T_target": min(max(self.chunk_size, 300), 700), "T_max": 800, "O": self.chunk_overlap}
        m_sent = st.median(sent_token_lengths)
        p95 = self._p95(sent_token_lengths)
        T_target = max(350, int(round(3 * m_sent)))
        T_target = min(max(T_target, 300), 700)
        O = min(max(int(0.25 * T_target), max(p95, 40)), 120)
        return {"T_min": 200, "T_target": T_target, "T_max": 800, "O": O}


    def chunk_text(
        self,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        paragraph_id = 0
        chunk_id = 0
        for paragraph in [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]:
            paragraph_id += 1
            for sentence in self._split_sentences(paragraph):
                sentence = self.normalizer.normalize_chunk_text(sentence)
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


    def _iter_sentences(self, block: Block) -> Iterable[str]:
        txt = self.normalizer.normalize_by_kind(block.kind, block.text)
        if block.kind in ("formula", "answer", "table_row"):
            yield txt
            return

        for s in self._split_sentences(txt):
            yield s


    def chunk_blocks(
        self,
        doc_id: str,
        blocks: List[Block],
        meta_doc: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        sent_lens = [self._est_tokens(s) for b in blocks if b.kind in ("paragraph", "list")
                     for s in self._split_sentences(b.text)]

        cfg = self._calc_targets(sent_lens)

        T_min, T_target, T_max, O = cfg["T_min"], cfg["T_target"], cfg["T_max"], cfg["O"]

        chunks: List[Dict[str, Any]] = []
        buf: List[str] = []
        buf_tok: int = 0
        parent: Dict[str, Any] | None = None
        pages: set[int] = set()

        def flush() -> None:
            nonlocal buf, buf_tok, parent, pages
            if not buf:
                return

            text = " ".join(buf).strip()
            if not text:
                buf = []
                buf_tok = 0
                parent = None
                pages = set()
                return

            ch = Chunk(
                id=str(uuid.uuid4()),
                text=text,
                tokens_est=self._est_tokens(text),
                parent_type=parent["kind"] if parent else "paragraph",
                pages=sorted(pages),
                parent_page_anchor=min(pages) if pages else None,
                meta={**(parent.get("meta", {}) if parent else {}), **meta_doc},
            )

            chunks.append(ch.__dict__)
            buf = []
            buf_tok = 0
            parent = None
            pages = set()

        for b in blocks:
            if b.kind == "heading":
                if buf_tok >= T_min:
                    flush()

                parent = {"kind": "heading+next", "meta": {"heading": self.normalizer.normalize_by_kind("heading", b.text)}}
                pages = {b.page}

                buf.append(parent["meta"]["heading"])
                buf_tok += self._est_tokens(buf[-1])
                continue

            if b.kind in ("table_row", "answer", "formula"):
                if buf_tok >= T_min:
                    flush()

                t = self.normalizer.normalize_by_kind(b.kind, b.text)
                if not self._valid_after_norm(t, allow_short=True, is_formula=(b.kind == "formula")):
                    continue

                parent = {"kind": b.kind, "meta": {**b.meta}}
                pages = {b.page}
                buf = [t]
                buf_tok = self._est_tokens(t)
                flush()
                continue

            if b.kind in ("paragraph", "list"):
                if parent is None:
                    parent = {"kind": b.kind, "meta": {}}
                pages.add(b.page)
                for stxt in self._iter_sentences(b):
                    if not self._valid_after_norm(stxt):
                        continue
                    token_count: int = self._est_tokens(stxt)

                    if buf_tok + token_count <= T_target or not buf:
                        buf.append(stxt)
                        buf_tok += token_count

                    else:
                        flush()
                        parent = {"kind": b.kind, "meta": {}}
                        pages = {b.page}
                        buf.append(stxt)
                        buf_tok = token_count
                continue

            if b.kind == "table_title":
                if parent is None:
                    parent = {"kind": "heading+next", "meta": {"table_title": b.text}}
                    pages = {b.page}
                else:
                    parent.setdefault("meta", {})["table_title"] = b.text
                continue

        if buf_tok > 0:
            flush()

        merged: List[Dict[str, Any]] = []
        for c in chunks:
            if merged and c["tokens_est"] < T_min and merged[-1]["parent_type"] == c["parent_type"]:
                merged[-1]["text"] += " " + c["text"]
                merged[-1]["tokens_est"] = self._est_tokens(merged[-1]["text"])
                merged[-1]["pages"] = sorted(set(merged[-1]["pages"]) | set(c["pages"]))
            else:
                merged.append(c)

        source_len = sum(len(b.text) for b in blocks if b.kind in ("paragraph", "list", "heading"))
        out_len = sum(len(c["text"]) for c in merged)
        coverage = out_len / max(1, source_len)
        logger.info(f"Chunking coverage={coverage:.3f}, chunks={len(merged)}, target={T_target}, overlap={O}")

        ChunkingLogger.log_chunking_results(
            doc_id=doc_id,
            extracted_text="",
            chunks=merged,
            metadata={**meta_doc, "coverage": coverage, "T_target": T_target, "overlap": O},
            paragraph_count=len(blocks),
        )

        return merged


    @staticmethod
    def validate_chunks(
        chunks: List[Dict[str, Any]],
        *,
        tmin: int = 200,
        tmax: int = 800
    ) -> Dict[str, Any]:
        flags = {"len": 0, "paren": 0, "dup": 0}
        seen = set()
        def _h(s: str) -> str:
            return hashlib.md5(s.encode("utf-8")).hexdigest()

        def _balanced(s: str, a: str, b: str) -> bool:
            return s.count(a) == s.count(b)

        for c in chunks:
            if c["parent_type"] not in ("answer", "formula"):
                if not (tmin <= c["tokens_est"] <= tmax):
                    c["flag_len"] = True
                    flags["len"] += 1

            if not (_balanced(c["text"], "(", ")") and _balanced(c["text"], "[", "]") and _balanced(c["text"], "{", "}")):
                c["flag_paren"] = True
                flags["paren"] += 1
            key = _h(c["text"])

            if key in seen:
                c["flag_dup"] = True
                flags["dup"] += 1
            seen.add(key)

        return {
            "counts": flags,
            "total": len(chunks)
        }

