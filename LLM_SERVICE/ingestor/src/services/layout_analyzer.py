from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import statistics as st
import re

from loguru import logger
from .text_normalize_service import TextNormalizeService
from src.data_classes.data_classes import OrderedLine


class LayoutAnalyzer:
    def __init__(
        self,
        *,
        column_max: int = 3,
        column_gap_tol: float = 0.035,
        header_footer_freq: float = 0.55
    ) -> None:
        self.column_max = column_max
        self.column_gap_tol = column_gap_tol
        self.header_footer_freq = header_footer_freq
        self.normalizer = TextNormalizeService()
        self._re_page_num = re.compile(r"^\s*\d{1,4}\s*$")
        self._re_rubric = re.compile(r"^(ИСТОРИИ НАУКИ|СОДЕРЖАНИЕ|БИБЛИОГРАФИЯ)\b", re.I)


    def _columns_by_x(
        self,
        lines: List[Dict[str, Any]],
        page_width: float
    ) -> List[Tuple[float,float]]:
        if not lines:
            return []
        mids = sorted([(ln["x0"] + ln["x1"]) * 0.5 for ln in lines])
        if not mids:
            return []

        buckets: List[List[float]] = []
        tol_px = self.column_gap_tol * page_width
        for m in mids:
            placed = False
            for b in buckets:
                if abs(m - st.mean(b)) <= tol_px:
                    b.append(m)
                    placed = True
                    break
            if not placed:
                buckets.append([m])
                if len(buckets) >= self.column_max:
                    break

        buckets = sorted(buckets, key=lambda b: st.mean(b))
        cols: List[Tuple[float,float]] = []
        for b in buckets:
            cmin, cmax = min(b), max(b)
            cols.append((cmin - tol_px, cmax + tol_px))
        return cols


    def _assign_column(
        self,
        ln: Dict[str, Any],
        cols: List[Tuple[float,float]]
    ) -> int:
        if not cols:
            return 0
        mid = (ln["x0"] + ln["x1"]) * 0.5
        best, bid = float("inf"), 0
        for i, (c0,c1) in enumerate(cols):
            c_mid = (c0 + c1) * 0.5
            d = abs(mid - c_mid)
            if d < best:
                best, bid = d, i
        return bid


    def _detect_headers_footers_text(
        self,
        pages_lines: List[Tuple[float, List[Dict[str,Any]]]],
        band: float = 0.10
    ) -> Tuple[set[str], set[str]]:
        tops: Dict[str,int] = {}
        bots: Dict[str,int] = {}

        n = len(pages_lines) or 1

        for H, lines in pages_lines:
            top_lines = [ln for ln in lines if (ln["top"] / H) <= band]
            bot_lines = [ln for ln in lines if (ln["bottom"] / H) >= (1 - band)]

            for ln in top_lines:
                s = ln["text"].strip()
                if len(s) >= 3 and not s.islower():
                    tops[s] = tops.get(s, 0) + 1

            for ln in bot_lines:
                s = ln["text"].strip()
                if len(s) >= 3 and not s.islower():
                    bots[s] = bots.get(s, 0) + 1

        top_rm = {s for s,c in tops.items() if c / n >= self.header_footer_freq}
        bot_rm = {s for s,c in bots.items() if c / n >= self.header_footer_freq}
        return top_rm, bot_rm


    def order_page_lines(
        self,
        page_idx: int,
        page_width: float,
        page_height: float,
        raw_lines: List[Dict[str, Any]],
        global_top_rm: set[str],
        global_bot_rm: set[str]
    ) -> List[OrderedLine]:
        filtered = []

        for ln in raw_lines:
            t = ln["text"].strip()
            if not t:
                continue
            if t in global_top_rm or t in global_bot_rm:
                continue
            if self._re_page_num.match(t):
                continue
            if self._re_rubric.match(t):
                continue
            filtered.append(ln)

        if not filtered:
            return []

        cols = self._columns_by_x(filtered, page_width)
        ordered = [
            OrderedLine(
                page=page_idx + 1,
                top=ln["top"], bottom=ln["bottom"],
                x0=ln["x0"], x1=ln["x1"],
                text=ln["text"],
                column=self._assign_column(ln, cols)
            )
            for ln in filtered
        ]

        ordered.sort(key=lambda L: (L.column, L.top, L.x0))
        return ordered


    def compute_global_header_footer(
        self,
        all_pages: List[Tuple[float, List[Dict[str, Any]]]]
    ) -> Tuple[set[str], set[str]]:
        return self._detect_headers_footers_text(all_pages)


