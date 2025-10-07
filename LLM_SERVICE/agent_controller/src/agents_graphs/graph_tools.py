from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.core.utils import EnvTools
from src.core.converters import DataConverter

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import ContextChunk, ContextDigestItem, GraphState

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
    def context_chunks_to_payload(chunks: list["ContextChunk"]) -> list[dict[str, object]]:
        return DataConverter.chunks_to_payload(chunks)


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
