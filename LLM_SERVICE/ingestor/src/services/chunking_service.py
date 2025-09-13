# chunking_service.py
from __future__ import annotations

import hashlib
import re
import uuid
from typing import List, Dict, Any, Iterable

import blingfire  # type: ignore
from loguru import logger
import statistics as st

from src.data_classes.data_classes import Block, Chunk
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
            return {"T_min": 126, "T_target": min(max(self.chunk_size, 189), 420), "T_max": 525, "O": self.chunk_overlap}
        m_sent = st.median(sent_token_lengths)
        p95 = self._p95(sent_token_lengths)
        T_target = max(210, int(round(2.52 * m_sent)))
        T_target = min(max(T_target, 168), 525)
        O = min(max(int(0.25 * T_target), max(p95, 42)), 84)
        return {"T_min": 168, "T_target": T_target, "T_max": 525, "O": O}




    def _iter_sentences(self, block: Block) -> Iterable[str]:
        txt = block.text
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

            text = self.normalizer.normalize_by_kind(parent["kind"] if parent else "paragraph", text)
            chunk = Chunk(
                id=str(uuid.uuid4()),
                text=text,
                tokens_est=self._est_tokens(text),
                parent_type=parent["kind"] if parent else "paragraph",
                pages=sorted(pages),
                parent_page_anchor=min(pages) if pages else None,
                meta={**(parent.get("meta", {}) if parent else {}), **meta_doc},
            )

            chunks.append(chunk.__dict__)
            buf = []
            buf_tok = 0
            parent = None
            pages = set()

        for b in blocks:
            if b.kind == "heading":
                if buf_tok >= T_min:
                    flush()

                parent = {"kind": "heading+next", "meta": {"heading": b.text}}
                pages = {b.page}

                buf.append(parent["meta"]["heading"])
                buf_tok += self._est_tokens(buf[-1])
                continue

            if b.kind in ("table_row", "answer", "formula"):
                if buf_tok >= T_min:
                    flush()

                t = b.text
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
                combined_pages = set(merged[-1]["pages"]) | set(c["pages"])
                if len(combined_pages) <= 4:
                    merged[-1]["text"] += " " + c["text"]
                    merged[-1]["tokens_est"] = self._est_tokens(merged[-1]["text"])
                    merged[-1]["pages"] = sorted(combined_pages)
                else:
                    merged.append(c)
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

        validation_result = self.validate_chunks(merged, tmin=T_min, tmax=T_max)
        
        for c in merged:
            if c.get("flag_ocr_spacing"):
                original_text = c["text"]
                fixed_text = self.normalizer._collapse_ocr_spacing(original_text)
                if fixed_text != original_text:
                    c["text"] = fixed_text
                    c["tokens_est"] = self._est_tokens(fixed_text)
                    c["flag_ocr_spacing"] = False
        
        logger.info(f"Chunk validation: {validation_result['counts']} issues out of {validation_result['total']} chunks")

        paragraph_id = 0
        chunk_id = 0
        out: List[Dict[str, Any]] = []
        for c in merged:
            paragraph_id += 1
            chunk_id += 1
            out.append({
                "id": c["id"],
                "doc_id": doc_id,
                "paragraph_id": paragraph_id,
                "chunk_id": chunk_id,
                "text": c["text"],
                "pages": c.get("pages", []),
                "page_anchor": c.get("parent_page_anchor"),
                "parent_type": c.get("parent_type"),
                "meta": c.get("meta", {}),
            })
        return out


    @staticmethod
    def validate_chunks(
        chunks: List[Dict[str, Any]],
        *,
        tmin: int = 200,
        tmax: int = 800,
        max_pages_span: int = 4,
        max_single_char_share: float = 0.35,
    ) -> Dict[str, Any]:
        import re, hashlib
        flags = {"len": 0, "paren": 0, "dup": 0, "alpha": 0, "single": 0, "ocr_space": 0, "pages": 0}
        seen = set()
        OCR_SPACING_RE = re.compile(r'\b(?:[A-Za-zА-Яа-я]\s){3,}[A-Za-zА-Яа-я]\b')

        def _h(s: str) -> str:
            return hashlib.md5(s.encode("utf-8")).hexdigest()

        def _balanced(s: str, a: str, b: str) -> bool:
            return s.count(a) == s.count(b)

        def _metrics(s: str) -> Dict[str, Any]:
            toks = s.split()
            letters = sum(ch.isalpha() for ch in s)
            alpha_ratio = letters / max(1, len(s))
            single_share = sum(1 for t in toks if len(t) == 1) / max(1, len(toks))
            mean_wlen = (sum(len(t) for t in toks) / max(1, len(toks)))
            return {"alpha_ratio": alpha_ratio, "single_share": single_share, "mean_wlen": mean_wlen}

        for c in chunks:
            txt = c["text"]
            if c["parent_type"] not in ("answer", "formula"):
                if not (tmin <= c.get("tokens_est", 0) <= tmax):
                    c["flag_len"] = True; flags["len"] += 1

            if not (_balanced(txt, "(", ")") and _balanced(txt, "[", "]") and _balanced(txt, "{", "}")):
                c["flag_paren"] = True; flags["paren"] += 1

            key = _h(txt)
            if key in seen:
                c["flag_dup"] = True; flags["dup"] += 1
            seen.add(key)

            m = _metrics(txt)
            if m["alpha_ratio"] < 0.45:
                c["flag_low_alpha"] = True; flags["alpha"] += 1
            if m["single_share"] > max_single_char_share:
                c["flag_single_char"] = True; flags["single"] += 1
            if OCR_SPACING_RE.search(txt):
                c["flag_ocr_spacing"] = True; flags["ocr_space"] += 1

            if len(set(c.get("pages", []) or [])) > max_pages_span:
                c["flag_pages_span"] = True; flags["pages"] += 1

        return {"counts": flags, "total": len(chunks)}



