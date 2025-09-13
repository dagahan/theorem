from __future__ import annotations

import io
import statistics

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple

import re

import chardet
from docx import Document
from loguru import logger
import pdfplumber

from .text_normalize_service import TextNormalizeService

from .data_classes import Block

from src.core.logging import FileParserLogger


class FileParserService:
    HEAD_RE = re.compile(r"^(Структура варианта|Кодификатор|Спецификация|Содержание)\b", re.I)
    TABLE_TITLE_RE = re.compile(r"^Таблица\s+\d+\b", re.I)
    ANSWER_RE = re.compile(r"^Ответ\s*:\s*", re.I)
    LIST_LEAD_RE = re.compile(r"^(\d+[\.\)]|[-•])\s+")
    FORMULA_HINT_RE = re.compile(r"[=+\-×÷∑∏∫∂√≤≥≠→←α-ωΑ-Ω]")

    def __init__(self) -> None:
        self.normalizer = TextNormalizeService()


    def extract_file_to_text(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        doc_id: str | None = None,
        metadata: Dict[str, Any] | None = None
    ) -> str:
        name = filename.lower().strip()
        extracted_text = ""
        parsing_method = ""
        success = True
        error_message = ""

        try:
            if name.endswith(".pdf") or (content_type or "").startswith("application/pdf"):
                extracted_text = self._from_pdf_plain(content)
                parsing_method = "pdf_plumber_plain"

            elif name.endswith(".docx") or (content_type or "") in {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            }:
                extracted_text = self._from_docx(content)
                parsing_method = "docx_python_docx"

            elif name.endswith(".txt") or (content_type or "").startswith("text/"):
                extracted_text = self._from_text(content)
                parsing_method = "text_chardet"

            else:
                extracted_text = self._from_text_or_binary(content)
                parsing_method = "text_or_binary_chardet"

        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Failed to parse file {filename}: {e}")
            extracted_text = ""

        if doc_id and metadata is not None:
            FileParserLogger.log_parsing_results(
                doc_id=doc_id,
                filename=filename,
                content_type=content_type or "unknown",
                extracted_text=extracted_text,
                metadata=metadata,
                parsing_method=parsing_method,
                success=success,
                error_message=error_message
            )

        return extracted_text


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
                    extra_attrs=["x0", "x1", "top", "bottom"],
                )

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


    def _from_pdf_plain(
        self,
        content: bytes
    ) -> str:
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:

                parts = []

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_parts = []

                        text = page.extract_text()

                        if text and text.strip():
                            page_parts.append(self.normalizer.normalize_chunk_text(text.strip()))

                        tables = page.extract_tables()
                        if tables:
                            for t_idx, table in enumerate(tables, start=1):
                                if table:
                                    table_text = self._format_table(table)
                                    if table_text:
                                        page_parts.append(f"Table {t_idx}:\n{table_text}")

                        if page_parts:
                            page_content = "\n\n".join(page_parts)
                            parts.append(f"--- Page {page_num} ---\n{page_content}")

                    except Exception as ex:
                        logger.warning(f"Failed to extract content from PDF page {page_num}: {ex}")
                        continue

                if not parts:
                    logger.warning("No content extracted from PDF")
                    return ""
                return "\n\n".join(parts).strip()

        except Exception as ex:
            logger.error(f"Failed to process PDF with pdfplumber: {ex}")
            return ""


    @staticmethod
    def _format_table(table: list[list[str | None]]) -> str:
        if not table:
            return ""
        try:
            max_widths: list[int] = []
            for row in table:
                for index, cell in enumerate(row):
                    cell_text = str(cell or "").strip()

                    if index >= len(max_widths):
                        max_widths.append(len(cell_text))

                    else:
                        max_widths[index] = max(max_widths[index], len(cell_text))

            formatted_rows = []

            for row in table:
                formatted_cells = []
                for index, cell in enumerate(row):
                    cell_text = str(cell or "").strip()
                    width = max_widths[index] if index < len(max_widths) else len(cell_text)
                    formatted_cells.append(cell_text.ljust(width))
                formatted_rows.append(" | ".join(formatted_cells))

            return "\n".join(formatted_rows)

        except Exception as e:
            logger.warning(f"Failed to format table: {e}")
            return "\n".join([" | ".join([str(cell or "") for cell in row]) for row in table])


    @staticmethod
    def _from_docx(content: bytes) -> str:
        bio = io.BytesIO(content)
        doc = Document(bio)
        parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(parts).strip()


    @staticmethod
    def _from_text(content: bytes) -> str:
        det = chardet.detect(content)
        enc = det.get("encoding") or "utf-8"
        try:
            return content.decode(enc, errors="replace").strip()
        except Exception:
            return content.decode("utf-8", errors="replace").strip()


    def _from_text_or_binary(
        self,
        content: bytes
    ) -> str:
        if not content:
            return ""

        sample = content[:4096]
        printable_ratio = sum(32 <= b <= 126 or b in (9, 10, 13) for b in sample) / max(1, len(sample))
        if printable_ratio < 0.6:
            return ""

        return self._from_text(content)


        