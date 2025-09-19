from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Final, List, Tuple, Set, Dict
from loguru import logger

from src.domain.models import (
    ContextBuilderRequest, ContextBuilderResponse, ContextChunk,
    DigestItem, EvidenceItem, HealthStatus
)


class ContextBuilderService:
    MAX_DIGEST_ITEMS: Final[int] = 10
    MAX_EVIDENCE_ITEMS: Final[int] = 15
    MAX_QUOTE_LENGTH: Final[int] = 200
    MIN_SCORE_THRESHOLD_ABS: Final[float] = 0.30
    DYN_THRESHOLD_RATIO: Final[float] = 0.35
    DIGEST_PER_DOC_QUOTA: Final[int] = 3
    EVIDENCE_PER_PARAGRAPH_QUOTA: Final[int] = 2
    EVIDENCE_PER_DOC_QUOTA: Final[int] = 4
    SHINGLE_K: Final[int] = 3
    JACCARD_DUP_THRESHOLD: Final[float] = 0.80


    def __init__(self) -> None:
        self._space_re: re.Pattern[str] = re.compile(r"\s+")
        self._sent_split_re: re.Pattern[str] = re.compile(r"(?<=[.!?])\s+")
        self._trash_prefix_re: re.Pattern[str] = re.compile(r"^(рис\.|табл\.|рисунок|таблица|примечание[:.]?)\s*", re.IGNORECASE)
        self._token_re: re.Pattern[str] = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")


    def get_health_status(self) -> HealthStatus:
        try:
            return HealthStatus(status="healthy", version="0.0.1")
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return HealthStatus(status="unhealthy", version="0.0.1")


    def build_context(
        self,
        request: ContextBuilderRequest
    ) -> ContextBuilderResponse:
        try:
            if not request.chunks:
                return self._empty_ok()

            filtered: List[ContextChunk] = self._filter_and_sort_chunks(request.chunks)
            digest_items: List[DigestItem] = self._build_digest(filtered)
            evidence_items: List[EvidenceItem] = self._build_evidence(filtered)

            context_text: str = self._format_context(digest_items, evidence_items)
            if len(context_text) > request.max_context_chars:
                context_text = self._truncate_context(context_text, request.max_context_chars)

            return ContextBuilderResponse(
                context_text=context_text,
                success=True
            )

        except Exception as ex:
            logger.error(f"Context building failed: {ex}")
            return ContextBuilderResponse(
                context_text="",
                success=False,
                error=str(ex)
            )


    def _filter_and_sort_chunks(
        self,
        chunks: List[ContextChunk]
    ) -> List[ContextChunk]:
        sorted_chunks: List[ContextChunk] = sorted(
            chunks,
            key=lambda c: (-float(c.score), str(c.doc_id), int(c.paragraph_id), int(c.chunk_id))
        )

        max_score: float = float(sorted_chunks[0].score)
        dyn_threshold: float = max(self.MIN_SCORE_THRESHOLD_ABS, max_score * self.DYN_THRESHOLD_RATIO)
        passed: List[ContextChunk] = [c for c in sorted_chunks if float(c.score) >= dyn_threshold]
        return passed or sorted_chunks[: min(len(sorted_chunks), 20)]


    def _build_digest(
        self,
        chunks: List[ContextChunk]
    ) -> List[DigestItem]:
        result: List[DigestItem] = []
        per_doc_count: Dict[str, int] = {}
        seen_signatures: List[Set[str]] = []

        for c in chunks:
            if len(result) >= self.MAX_DIGEST_ITEMS:
                break

            if per_doc_count.get(c.doc_id, 0) >= self.DIGEST_PER_DOC_QUOTA:
                continue

            fact: str = self._key_sentence(c.text, target_len=140)
            if not fact:
                continue

            sig: Set[str] = self._signature(fact)

            if self._is_duplicate(sig, seen_signatures, self.JACCARD_DUP_THRESHOLD):
                continue

            result.append(DigestItem(fact=fact, doc_id=c.doc_id, paragraph_id=c.paragraph_id, chunk_id=c.chunk_id))
            per_doc_count[c.doc_id] = per_doc_count.get(c.doc_id, 0) + 1
            seen_signatures.append(sig)

        return result


    def _build_evidence(
        self,
        chunks: List[ContextChunk]
    ) -> List[EvidenceItem]:
        result: List[EvidenceItem] = []
        per_paragraph_count: Dict[Tuple[str, int], int] = {}
        per_doc_count: Dict[str, int] = {}

        for c in chunks:
            if len(result) >= self.MAX_EVIDENCE_ITEMS:
                break

            key_par: Tuple[str, int] = (c.doc_id, c.paragraph_id)
            if per_paragraph_count.get(key_par, 0) >= self.EVIDENCE_PER_PARAGRAPH_QUOTA:
                continue

            if per_doc_count.get(c.doc_id, 0) >= self.EVIDENCE_PER_DOC_QUOTA:
                continue

            quote: str = self._quote(c.text, self.MAX_QUOTE_LENGTH)
            if not quote:
                continue

            result.append(EvidenceItem(
                quote=quote,
                doc_id=c.doc_id,
                paragraph_id=c.paragraph_id,
                chunk_id=c.chunk_id,
                pages=c.pages,
                score=float(c.score),
            ))

            per_paragraph_count[key_par] = per_paragraph_count.get(key_par, 0) + 1
            per_doc_count[c.doc_id] = per_doc_count.get(c.doc_id, 0) + 1

        return result


    def _normalize(
        self,
        text: str
    ) -> str:
        t: str = unicodedata.normalize("NFKC", text or "")
        t = self._space_re.sub(" ", t).strip()
        return t


    def _split_sentences(
        self,
        text: str
    ) -> List[str]:
        t: str = self._normalize(text)
        if not t:
            return []

        raw: List[str] = self._sent_split_re.split(t)
        out: List[str] = []

        for part in raw:
            s: str = self._trash_prefix_re.sub("", part.strip(" „""'()[]"))
            s = self._space_re.sub(" ", s).strip()
            if s:
                out.append(s)

        return out


    def _key_sentence(
        self,
        text: str,
        target_len: int
    ) -> str:
        sents: List[str] = self._split_sentences(text)

        if not sents:
            return ""

        cand: str = sents[0]

        if len(cand) < 20 and len(sents) > 1:
            cand = (cand + " " + sents[1]).strip()

        if len(cand) > target_len:
            trimmed: str = cand[: target_len - 1].rstrip()
            last_space: int = trimmed.rfind(" ")
            if last_space >= 60:
                trimmed = trimmed[:last_space]
            cand = trimmed + "…"

        return cand


    def _quote(
        self,
        text: str,
        max_len: int
    ) -> str:
        sents: List[str] = self._split_sentences(text)

        if not sents:
            return ""

        q: str = sents[0]

        if len(q) < max_len // 2 and len(sents) > 1:
            q = (q + " " + sents[1]).strip()

        if len(q) > max_len:
            trimmed: str = q[: max_len - 1].rstrip()
            last_space: int = trimmed.rfind(" ")
            if last_space >= max_len // 3:
                trimmed = trimmed[:last_space]
            q = trimmed + "…"

        return q


    def _tokens(
        self,
        text: str
    ) -> List[str]:
        return [m.group(0).lower() for m in self._token_re.finditer(text)]


    def _shingles(
        self,
        toks: List[str],
        k: int
    ) -> Set[str]:
        if len(toks) < k:
            return set([" ".join(toks)]) if toks else set()
        return {" ".join(toks[i:i+k]) for i in range(len(toks) - k + 1)}


    def _signature(
        self,
        text: str
    ) -> Set[str]:
        toks: List[str] = self._tokens(text)
        return self._shingles(toks, self.SHINGLE_K)


    def _jaccard(
        self,
        a: Set[str],
        b: Set[str]
    ) -> float:
        if not a and not b:
            return 1.0
        inter: int = len(a & b)
        union: int = len(a | b) or 1
        return inter / union


    def _is_duplicate(
        self,
        sig: Set[str],
        seen: List[Set[str]],
        threshold: float
    ) -> bool:
        for s in seen:
            if self._jaccard(sig, s) >= threshold:
                return True
        return False


    def _format_context(
        self,
        digest: List[DigestItem],
        evidence: List[EvidenceItem]
    ) -> str:
        snapshot: str = datetime.now().strftime("%Y-%m-%d")
        parts: List[str] = [
            "RETRIEVER_CONTEXT_START",
            f"snapshot={snapshot}",
            "# digest",
        ]

        for d in digest:
            parts.append(f"- {d.fact} [doc#{d.doc_id}#p#{d.paragraph_id}#c#{d.chunk_id}]")
            
        parts.append("# evidence")

        for e in evidence:
            pages_str: str = ",".join(map(str, e.pages))
            parts.append(
                f"- id:doc#{e.doc_id}#p#{e.paragraph_id}#c#{e.chunk_id} | "
                f"score:{e.score:.5f} | pages:{pages_str} | \"{e.quote}\""
            )

        parts.append("RETRIEVER_CONTEXT_END")
        return "\n".join(parts)


    def _truncate_context(
        self,
        context_text: str,
        max_chars: int
    ) -> str:
        if len(context_text) <= max_chars:
            return context_text

        lines: List[str] = context_text.split("\n")
        out: List[str] = []
        cur: int = 0

        for ln in lines:
            if cur + len(ln) + 1 > max_chars:
                break
            out.append(ln)
            cur += len(ln) + 1

        if out and out[-1] != "RETRIEVER_CONTEXT_END":
            out.append("RETRIEVER_CONTEXT_END")

        return "\n".join(out)


    def _empty_ok(self) -> ContextBuilderResponse:
        return ContextBuilderResponse(
            context_text=(
                "RETRIEVER_CONTEXT_START\n"
                "snapshot=2024-01-01\n"
                "# digest\n- No relevant context found\n"
                "# evidence\n- No evidence available\n"
                "RETRIEVER_CONTEXT_END"
            ),
            success=True
        )


