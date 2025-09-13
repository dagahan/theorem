from __future__ import annotations

import io
import statistics
from typing import List, Dict, Any
import re
from loguru import logger
import pdfplumber

from .text_normalize_service import TextNormalizeService

from src.data_classes.data_classes import Block

from src.core.logging import FileParserLogger, TextNormalizeLogger, BlockingLogger


class FileParserService:
    HEAD_RE = re.compile(r"^(Структура варианта|Кодификатор|Спецификация|Содержание)\b", re.I)
    TABLE_TITLE_RE = re.compile(r"^Таблица\s+\d+\b", re.I)
    ANSWER_RE = re.compile(r"^Ответ\s*:\s*", re.I)
    LIST_LEAD_RE = re.compile(r"^(\d+[\.\)]|[-•])\s+")
    FORMULA_HINT_RE = re.compile(r"[=+\-×÷∑∏∫∂√≤≥≠→←α-ωΑ-Ω]")

    def __init__(self) -> None:
        self.normalizer = TextNormalizeService()


    def extract_blocks_from_pdf(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        doc_id: str | None = None,
        metadata: Dict[str, Any] | None = None
    ) -> List[Block]:
        name = filename.lower().strip()
        blocks: List[Block] = []
        parsing_method = "pdf_blocks_extraction"
        success = True
        error_message = ""

        try:
            if not (name.endswith(".pdf") or (content_type or "").startswith("application/pdf")):
                raise ValueError("Only PDF files are supported")
            
            blocks = self.extract_blocks(content)
            
            logger.info(f"Document {doc_id} blocked: {len(blocks)} blocks extracted")
            
            if doc_id:
                blocks_data = [
                    {
                        "page": block.page,
                        "kind": block.kind,
                        "text": block.text,
                        "bbox": block.bbox,
                        "meta": block.meta
                    }
                    for block in blocks
                ]
                BlockingLogger.log_blocking_results(
                    doc_id=doc_id,
                    filename=filename,
                    content_type=content_type or "unknown",
                    blocks=blocks_data,
                    metadata=metadata or {},
                    success=True
                )
            
            original_text_length = sum(len(block.text) for block in blocks)
            
            normalized_blocks = []
            for block in blocks:
                normalized_text = self.normalizer.normalize_by_kind(block.kind, block.text)
                normalized_block = Block(
                    text=normalized_text,
                    kind=block.kind,
                    page=block.page,
                    bbox=block.bbox,
                    meta=block.meta
                )
                normalized_blocks.append(normalized_block)
            
            blocks = normalized_blocks
            normalized_text_length = sum(len(block.text) for block in blocks)
            
            logger.info(f"Document {doc_id} normalized: {len(blocks)} blocks processed")
            logger.info(f"Text normalization: {original_text_length} -> {normalized_text_length} chars")
            
            if doc_id:
                TextNormalizeLogger.log_normalization_results(
                    doc_id=doc_id,
                    normalized_text="\n\n".join([block.text for block in blocks]),
                    metadata=metadata or {},
                    original_length=original_text_length,
                    normalized_length=normalized_text_length
                )

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Failed to parse PDF file {filename}: {e}")
            
            if doc_id:
                BlockingLogger.log_blocking_results(
                    doc_id=doc_id,
                    filename=filename,
                    content_type=content_type or "unknown",
                    blocks=[],
                    metadata=metadata or {},
                    success=False,
                    error_message=error_message
                )

        if doc_id and metadata is not None:
            FileParserLogger.log_parsing_results(
                doc_id=doc_id,
                filename=filename,
                content_type=content_type or "unknown",
                extracted_text="\n\n".join([block.text for block in blocks]),
                metadata=metadata,
                parsing_method=parsing_method,
                success=success,
                error_message=error_message
            )

        return blocks


    def extract_blocks(
        self,
        pdf_bytes: bytes
    ) -> List[Block]:
        blocks: List[Block] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages_lines = []
            for p in pdf.pages:
                words = p.extract_words(
                    use_text_flow=True,
                    keep_blank_chars=False,
                    x_tolerance=2.5,
                    y_tolerance=1.5,
                    extra_attrs=["x0", "x1", "top", "bottom", "size"]
                )

                def _glue_letter_splits(ws: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
                    if not ws: return ws
                    glued = [ws[0].copy()]
                    for w in ws[1:]:
                        prev = glued[-1]
                        gap = w["x0"] - prev["x1"]
                        avg_sz = (float(prev.get("size") or 10) + float(w.get("size") or 10)) / 2.0
                        if len(prev["text"]) == 1 and len(w["text"]) == 1 and gap >= 0 and gap < 0.6 * avg_sz:
                            prev["text"] += w["text"]
                            prev["x1"] = w["x1"]
                        else:
                            glued.append(w.copy())
                    return glued

                words = _glue_letter_splits(words)

                lines_map: Dict[float, List[Dict[str, Any]]] = {}
                for w in words:
                    key = round(w["top"], 1)
                    lines_map.setdefault(key, []).append(w)

                lines = []

                for key in sorted(lines_map):
                    items = sorted(lines_map[key], key=lambda ww: ww["x0"])
                    text = " ".join(it["text"] for it in items)
                    x0 = min(it["x0"] for it in items)
                    x1 = max(it["x1"] for it in items)
                    top = min(it["top"] for it in items)
                    bottom = max(it["bottom"] for it in items)
                    lines.append({"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom})

                pages_lines.append((p.height, lines))

            top_rm, bot_rm = self._detect_headers_footers(pages_lines)

            for page_idx, (H, lines) in enumerate(pages_lines, start=1):
                clean = [ln for ln in lines if ln["text"].strip() not in top_rm | bot_rm]

                gaps = [clean[i + 1]["top"] - clean[i]["bottom"] for i in range(len(clean) - 1)]
                y_gap = statistics.median(gaps) if gaps else 4.0
                paras = self._merge_lines_to_paragraphs(clean, y_gap * 1.5)

                for s in paras:
                    raw = s.strip()

                    if self.TABLE_TITLE_RE.match(raw):
                        txt = self.normalizer.normalize_by_kind("heading", raw)
                        blocks.append(Block(page_idx, "table_title", txt, (0, 0, 0, 0), {}))

                    elif self.HEAD_RE.match(raw):
                        txt = self.normalizer.normalize_by_kind("heading", raw)
                        blocks.append(Block(page_idx, "heading", txt, (0, 0, 0, 0), {}))

                    elif self.ANSWER_RE.match(raw):
                        txt = self.normalizer.normalize_by_kind("paragraph", raw)
                        blocks.append(Block(page_idx, "answer", txt, (0, 0, 0, 0), {}))

                    elif self.LIST_LEAD_RE.match(raw):
                        txt = self.normalizer.normalize_by_kind("list", raw)
                        blocks.append(Block(page_idx, "list", txt, (0, 0, 0, 0), {}))

                    elif self.FORMULA_HINT_RE.search(raw):
                        txt = self.normalizer.normalize_by_kind("formula", raw)
                        blocks.append(Block(page_idx, "formula", txt, (0, 0, 0, 0), {}))

                    else:
                        txt = self.normalizer.normalize_by_kind("paragraph", raw)
                        blocks.append(Block(page_idx, "paragraph", txt, (0, 0, 0, 0), {}))

            table_rows, tables_json = self.linearize_tables(pdf_bytes)
            for tr in table_rows:
                blocks.append(Block(tr["page"], "table_row", tr["text"], (0, 0, 0, 0), tr["meta"]))

        return blocks


    def linearize_tables(
        self,
        pdf_bytes: bytes
    ) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
        rows_out: List[Dict[str, Any]] = []
        json_out: List[Dict[str, Any]] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                for t_idx, tbl in enumerate(page.extract_tables() or []):
                    tid = f"T{page_idx}_{t_idx + 1}"
                    header = tbl[0] if tbl else None

                    jrows = []

                    for r_idx, row in enumerate(tbl):
                        cells = [(c or "").strip() for c in row]
                        jrows.append(
                            {"row_idx": r_idx, "cells": [{"col": i, "text": cells[i]} for i in range(len(cells))]}
                        )

                        if r_idx == 0 and header:
                            h = " ; ".join(f"C{i+1}={header[i].strip() if header[i] else ''}" for i in range(len(header)))
                            text = f"[TABLE {tid}] Header: {h}"
                            rows_out.append({
                                "page": page_idx,
                                "text": self.normalizer.normalize_by_kind("table_row", text),
                                "meta": {"table_id": tid, "row_idx": 0, "header": True},
                            })

                        else:
                            s = " ; ".join(f"C{i+1}={cells[i]}" for i in range(len(cells)))
                            text = f"[TABLE {tid} R{r_idx}] {s}"
                            rows_out.append({
                                "page": page_idx,
                                "text": self.normalizer.normalize_by_kind("table_row", text),
                                "meta": {"table_id": tid, "row_idx": r_idx, "header": False},
                            })

                    json_out.append({"table_id": tid, "page": page_idx, "rows": jrows, "header_present": bool(header)})
        return rows_out, json_out


    @staticmethod
    def _detect_headers_footers(
        pages_words: List[tuple[float, List[Dict[str, Any]]]],
        hband: float = 0.10,
        min_freq: float = 0.5
    ) -> tuple[set[str], set[str]]:
        tops: Dict[str, int] = {}
        bottoms: Dict[str, int] = {}
        n = len(pages_words)

        for H, words in pages_words:
            top_lines = [ln for ln in words if ln["top"] / H <= hband]
            bot_lines = [ln for ln in words if (ln["bottom"]) / H >= (1 - hband)]

            for ln in top_lines:
                s = ln["text"].strip()
                if len(s) >= 5:
                    tops[s] = tops.get(s, 0) + 1

            for ln in bot_lines:
                s = ln["text"].strip()
                if len(s) >= 5:
                    bottoms[s] = bottoms.get(s, 0) + 1

        top_rm = {s for s, c in tops.items() if c / n >= min_freq}
        bot_rm = {s for s, c in bottoms.items() if c / n >= min_freq}
        return top_rm, bot_rm


    @staticmethod
    def _merge_lines_to_paragraphs(
        lines: List[Dict[str, Any]],
        y_gap: float
    ) -> List[str]:
        out, buf, last_bottom = [], [], None
        for ln in lines:
            if last_bottom is not None and ln["top"] - last_bottom > y_gap:
                out.append(" ".join(buf))
                buf = []
            buf.append(ln["text"])
            last_bottom = ln["bottom"]
        if buf:
            out.append(" ".join(buf))
        return out




        