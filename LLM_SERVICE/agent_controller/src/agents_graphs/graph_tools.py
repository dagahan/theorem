from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.core.utils import EnvTools
from src.core.converters import DataConverter

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import ContextDigestItem, GraphState

DEFAULT_MAX_CONTEXT_CHARS = 2048


class GraphTools:
    @staticmethod
    def mark_failure(
        state: "GraphState",
        message: str
    ) -> "GraphState":
        state['success'] = False
        state['error'] = message
        return state


    @staticmethod
    def record_timing(
        state: "GraphState",
        key: str, started_at: float
    ) -> float:
        duration_ms = (time.time() - started_at) * 1000.0
        timings = state.setdefault('timings_ms', {})
        timings[key] = duration_ms
        return duration_ms


    @staticmethod
    def total_elapsed_ms(state: "GraphState") -> float:
        started_at = state.get('started_at_ms')
        if started_at is None:
            started = time.time() * 1000.0
        else:
            try:
                started = float(started_at)
            except (TypeError, ValueError):
                started = time.time() * 1000.0

        now_ms = time.time() * 1000.0

        return max(0.0, now_ms - started)




    @staticmethod
    def digests_to_payload(digests: list["ContextDigestItem"]) -> list[dict[str, object]]:
        return DataConverter.digests_to_payload(digests)


    @staticmethod
    def digests_to_json(digests: list["ContextDigestItem"]) -> str:
        return DataConverter.digests_to_json(digests)


    @staticmethod
    def resolve_default_max_context_chars() -> int:
        raw_value = EnvTools.load_env_var('VLLM_TALKING_MAX_LEN')
        if raw_value:
            try:
                computed = int(float(raw_value) / 2)
                if computed > 0:
                    return computed

            except (TypeError, ValueError):
                logger.warning(
                    f"Failed to parse VLLM_TALKING_MAX_LEN={raw_value!r}, falling back to {DEFAULT_MAX_CONTEXT_CHARS}",
                )

        return DEFAULT_MAX_CONTEXT_CHARS


    @staticmethod
    def resolve_max_context_chars(
        candidate: Any,
        fallback: int
    ) -> int:
        parsed: int | None = None

        if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
            parsed = int(candidate)

        elif isinstance(candidate, str):
            stripped = candidate.strip()
            if stripped:
                try:
                    parsed = int(float(stripped))
                except ValueError:
                    logger.warning(
                        f"Invalid string for max_context_chars={candidate!r}, falling back to {fallback}",
                    )

        if parsed is None or parsed <= 0:
            if parsed not in (None, fallback):
                logger.warning(
                    f"Using fallback max_context_chars={fallback} (received {candidate!r})",
                )
                
            return fallback

        return parsed


    @staticmethod
    def debit_tokens(state: "GraphState", approx_chars: int) -> None:
        budgets = state.get('budgets', {})
        tokens_left = int(budgets.get('tokens_left', 0))
        spent = max(1, int(approx_chars / 4))
        budgets['tokens_left'] = max(0, tokens_left - spent)
        state['budgets'] = budgets


    @staticmethod
    def deadline_exceeded(state: "GraphState") -> bool:
        b = state.get('budgets', {})
        return (time.time() * 1000.0) >= float(b.get('deadline_at_ms', 0.0))


    @staticmethod
    def merge_claims(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for c in existing or []:
            if isinstance(c, dict) and c.get('claim_id'):
                by_id[c['claim_id']] = c
        for c in new or []:
            cid = c.get('claim_id')
            if not cid:
                continue
            if cid in by_id:
                base = by_id[cid]
                base['support'] = int(base.get('support', 0)) + int(c.get('support', 0))
                base['contradict'] = int(base.get('contradict', 0)) + int(c.get('contradict', 0))
                try:
                    base_conf = float(base.get('confidence', 0.0))
                    new_conf = float(c.get('confidence', 0.0))
                    base['confidence'] = max(0.0, min(1.0, (base_conf + new_conf) / 2.0))
                except Exception:
                    pass
            else:
                by_id[cid] = c
        return list(by_id.values())


    @staticmethod
    def build_cycle_summary(question: str, subgoals: list[dict[str, Any]], claims: list[dict[str, Any]], budgets: dict[str, Any], gatekeeper_feedback: dict[str, Any] | None = None, context_digests: list[Any] | None = None) -> dict[str, Any]:
        if context_digests:
            top_digests = context_digests[:8]  # Take first 8 digests
            top_claims = [{"id": f"digest_{i}", "t": d.summary} for i, d in enumerate(top_digests)]
        else:
            top_claims = sorted(claims or [], key=lambda x: float(x.get('confidence', 0.0)), reverse=True)[:8]
        
        summary = {
            "question": question,
            "open_subgoals": [g.get('id') for g in (subgoals or []) if not g.get('done')],
            "top_claims": top_claims,
            "budget": {
                "tokens_left": int(budgets.get('tokens_left', 0)),
                "deadline_at_ms": float(budgets.get('deadline_at_ms', 0.0)),
                "max_iters": int(budgets.get('max_iters', 0)),
            }
        }
        
        if gatekeeper_feedback:
            summary["gatekeeper_feedback"] = {
                "missing_subgoals": gatekeeper_feedback.get('missing_subgoals', []),
                "next_hints": gatekeeper_feedback.get('next_hints', []),
                "contradictions": gatekeeper_feedback.get('contradictions', []),
                "coverage": gatekeeper_feedback.get('coverage', 0.0),
                "confidence_summary": gatekeeper_feedback.get('confidence_summary', ''),
            }
        
        return summary
