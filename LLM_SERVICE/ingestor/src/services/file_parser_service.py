from __future__ import annotations

import io
import math
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Set, Optional
import re
from loguru import logger
import pdfplumber

from .text_normalize_service import TextNormalizeService

from src.data_classes.data_classes import Block

from src.core.logging import FileParserLogger, TextNormalizeLogger, BlockingLogger


@dataclass(frozen=True)
class TextCharacter:
    character: str
    x0: float
    x1: float
    top: float
    bottom: float
    page: int


@dataclass(frozen=True)
class TextLine:
    page: int
    top: float
    bottom: float
    x0: float
    x1: float
    text: str
    character_spans: List[Tuple[int, int]]


@dataclass(frozen=True)
class PageParseResult:
    doc_id: str
    page_index: int
    width: float
    height: float
    lines: List[TextLine]
    normalized_text: str
    original_length: int
    normalized_length: int


RUSSIAN_LETTERS = "А-Яа-яЁё"
WORD_PATTERN = re.compile(rf"[0-9A-Za-z{RUSSIAN_LETTERS}]+")


class FileParserService:
    HEAD_PATTERNS = re.compile(
        rf"^((раздел|глава|приложение)\s+[IVXLC\d]+|[IVXLC]+\.\s+|[A-ZА-ЯЁ][\w{RUSSIAN_LETTERS}-]{{1,25}}:?$)",
        re.IGNORECASE
    )
    TABLE_TITLE_PATTERN = re.compile(r"^Таблица\s+\d+\b", re.I)
    ANSWER_PATTERN = re.compile(r"^Ответ\s*:\s*", re.I)
    LIST_LEAD_PATTERN = re.compile(r"^(\d+[\.\)]|[-•])\s+")
    FORMULA_PATTERN = re.compile(r"[=+\-×÷∑∏∫∂√≤≥≠→←α-ωΑ-Ω]")

    def __init__(self, line_merge_tolerance_ratio: float = 0.65, min_line_characters: int = 2) -> None:
        self.line_merge_tolerance_ratio = line_merge_tolerance_ratio
        self.min_line_characters = min_line_characters
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
        parsing_method = "enhanced_pdf_parsing"
        success = True
        error_message = ""

        try:
            if not (name.endswith(".pdf") or (content_type or "").startswith("application/pdf")):
                raise ValueError("Only PDF files are supported")
            
            page_results = self.parse_pdf_with_character_layer(content, doc_id or "unknown")
            blocks = self.convert_page_results_to_blocks(page_results)
            
            logger.info(f"Document {doc_id} parsed: {len(blocks)} blocks extracted from {len(page_results)} pages")
            
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


    def parse_pdf_with_character_layer(self, pdf_bytes: bytes, doc_id: str) -> List[PageParseResult]:
        results: List[PageParseResult] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_result = self._parse_page_with_characters(doc_id, page_index, page)
                results.append(page_result)
        return results

    def _parse_page_with_characters(self, doc_id: str, page_index: int, page: pdfplumber.page.Page) -> PageParseResult:
        width = float(page.width)
        height = float(page.height)

        characters = self._extract_characters_from_page(page, page_index)
        if not characters:
            return PageParseResult(
                doc_id=doc_id,
                page_index=page_index,
                width=width,
                height=height,
                lines=[],
                normalized_text="",
                original_length=0,
                normalized_length=0
            )

        lines = self._cluster_characters_into_lines(characters)
        text_lines = self._reconstruct_text_lines(lines)
        
        page_text = "\n".join(line.text for line in text_lines)
        normalized_text = self._normalize_page_text(page_text)

        return PageParseResult(
            doc_id=doc_id,
            page_index=page_index,
            width=width,
            height=height,
            lines=text_lines,
            normalized_text=normalized_text,
            original_length=sum(len(line.text) for line in text_lines),
            normalized_length=len(normalized_text)
        )

    def _extract_characters_from_page(self, page: pdfplumber.page.Page, page_index: int) -> List[TextCharacter]:
        characters = []
        for char_data in page.chars:
            character = char_data.get("text", "")
            if not character or character in ("\u0000", "\u0001", "\u0002"):
                continue
            
            characters.append(TextCharacter(
                character=character,
                x0=float(char_data["x0"]),
                x1=float(char_data["x1"]),
                top=float(char_data["top"]),
                bottom=float(char_data["bottom"]),
                page=page_index
            ))
        return characters

    def _cluster_characters_into_lines(self, characters: List[TextCharacter]) -> List[List[TextCharacter]]:
        if not characters:
            return []

        median_height = statistics.median([c.bottom - c.top for c in characters]) or 10.0
        y_tolerance = median_height * self.line_merge_tolerance_ratio

        characters_sorted = sorted(characters, key=lambda c: (c.top, c.x0))
        lines = []
        current_line: List[TextCharacter] = []
        current_top: Optional[float] = None

        for char in characters_sorted:
            if not current_line:
                current_line = [char]
                current_top = char.top
                continue

            if current_top is not None and abs(char.top - current_top) <= y_tolerance:
                current_line.append(char)
            else:
                lines.append(current_line)
                current_line = [char]
                current_top = char.top

        if current_line:
            lines.append(current_line)

        return [line for line in lines if len(line) >= self.min_line_characters]

    def _reconstruct_text_lines(self, character_lines: List[List[TextCharacter]]) -> List[TextLine]:
        text_lines = []
        
        for line_characters in character_lines:
            line_characters_sorted = sorted(line_characters, key=lambda c: (c.top, c.x0))
            
            line_text, line_x0, line_x1, character_spans = self._reconstruct_line_text(line_characters_sorted)
            
            if not line_text.strip():
                continue

            normalized_text = self._normalize_line_text(line_text)

            text_line = TextLine(
                page=line_characters_sorted[0].page,
                top=min(c.top for c in line_characters_sorted),
                bottom=max(c.bottom for c in line_characters_sorted),
                x0=line_x0,
                x1=line_x1,
                text=normalized_text,
                character_spans=character_spans
            )
            text_lines.append(text_line)

        return text_lines

    def _reconstruct_line_text(self, line_characters: List[TextCharacter]) -> Tuple[str, float, float, List[Tuple[int, int]]]:
        if not line_characters:
            return "", 0.0, 0.0, []

        gaps = []
        for i in range(len(line_characters) - 1):
            gap = max(0.0, line_characters[i + 1].x0 - line_characters[i].x1)
            gaps.append(gap)

        gap_threshold = self._estimate_gap_threshold(gaps)
        if gap_threshold <= 0.0:
            median_gap = statistics.median(gaps) if gaps else 1.0
            gap_threshold = median_gap * 1.8

        text_parts = []
        character_spans = []
        current_offset = 0

        for i, char in enumerate(line_characters):
            if i == 0:
                text_parts.append(char.character)
                character_spans.append((current_offset, current_offset + len(char.character)))
                current_offset += len(char.character)
            else:
                gap = max(0.0, line_characters[i].x0 - line_characters[i - 1].x1)
                if gap >= gap_threshold:
                    text_parts.append(" ")
                    current_offset += 1
                
                text_parts.append(char.character)
                character_spans.append((current_offset, current_offset + len(char.character)))
                current_offset += len(char.character)

        text = "".join(text_parts)
        text = re.sub(r"[ \t]{2,}", " ", text)

        x0 = min(c.x0 for c in line_characters)
        x1 = max(c.x1 for c in line_characters)

        return text, x0, x1, character_spans

    def _normalize_line_text(self, text: str) -> str:
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"\s-\s", " — ", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        
        text = re.sub(r'\b([а-яё])\s+([а-яё])\b', r'\1\2', text, flags=re.IGNORECASE)
        text = re.sub(r'\b([a-z])\s+([a-z])\b', r'\1\2', text, flags=re.IGNORECASE)
        
        return text

    def _normalize_page_text(self, text: str) -> str:
        text = re.sub(r"(?:^|\s)([Nn])\s*(\d+)", r" № \2", text)
        text = re.sub(r"-\n(?=\S)", "", text)
        text = re.sub(r"\s+([\)\]\}•])", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def convert_page_results_to_blocks(self, page_results: List[PageParseResult]) -> List[Block]:
        blocks = []

        for page_result in page_results:
            for line in page_result.lines:
                text = line.text.strip()
                if not text:
                    continue

                block_kind = self._classify_text_kind(text)
                normalized_text = self.normalizer.normalize_by_kind(block_kind, text)

                block = Block(
                    page=line.page + 1,
                    kind=block_kind,
                    text=normalized_text,
                    bbox=(line.x0, line.top, line.x1, line.bottom),
                    meta={"character_spans": line.character_spans}
                )
                blocks.append(block)

        return blocks

    def _classify_text_kind(self, text: str) -> str:
        text_clean = text.strip()
        
        if self.TABLE_TITLE_PATTERN.match(text_clean):
            return "table_title"
        elif self.HEAD_PATTERNS.match(text_clean):
            return "heading"
        elif self.ANSWER_PATTERN.match(text_clean):
            return "answer"
        elif self.LIST_LEAD_PATTERN.match(text_clean):
            return "list"
        elif self.FORMULA_PATTERN.search(text_clean):
            return "formula"
        elif len(text_clean) < 10:
            return "paragraph"
        else:
            return "paragraph"


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

    def _estimate_gap_threshold(self, gaps: List[float]) -> float:
        if len(gaps) < 2:
            return statistics.median(gaps) * 1.6 if gaps else 1.0

        gaps_sorted = sorted(gaps)
        center1 = self._percentile(gaps_sorted, 0.25)
        center2 = self._percentile(gaps_sorted, 0.75)

        if center1 == center2:
            return center1 or 1.0

        for _ in range(6):
            cluster1: List[float] = []
            cluster2: List[float] = []
            for gap in gaps:
                (cluster1 if abs(gap - center1) < abs(gap - center2) else cluster2).append(gap)
            
            if cluster1:
                center1 = sum(cluster1) / len(cluster1)
            if cluster2:
                center2 = sum(cluster2) / len(cluster2)

        if center1 > center2:
            center1, center2 = center2, center1

        return (center1 + center2) / 2.0

    def _percentile(self, sorted_values: List[float], percentile: float) -> float:
        if not sorted_values:
            return 0.0
        if percentile <= 0:
            return sorted_values[0]
        if percentile >= 1:
            return sorted_values[-1]
        
        index = percentile * (len(sorted_values) - 1)
        low = int(math.floor(index))
        high = int(math.ceil(index))
        
        if low == high:
            return sorted_values[low]
        
        fraction = index - low
        return sorted_values[low] * (1 - fraction) + sorted_values[high] * fraction




        