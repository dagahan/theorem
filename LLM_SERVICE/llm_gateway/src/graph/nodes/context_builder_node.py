from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List

from loguru import logger

from src.graph.graph_utils import timeout_and_retry
from src.domain.models import ContextBuilderRequest, ContextChunk

if TYPE_CHECKING:
    from src.adapters.context_builder_adapter import ContextBuilderAdapter
    from src.domain.models import GraphState


class ContextBuilderNode:
    def __init__(self, context_builder_service: "ContextBuilderAdapter") -> None:
        self.context_builder_service = context_builder_service


    @timeout_and_retry(max_attempts=3, timeout_sec=25.0)
    async def execute_node(self, graph_state: "GraphState") -> "GraphState":
        t0: float = time.time()

        retrieved_chunks: List[Any] = graph_state.get("context_chunks", []) or []
        max_context_chars: int = int(graph_state.get("max_context_chars", 4000))

        timings: Dict[str, float] = graph_state.setdefault("timings_ms", {})

        if not retrieved_chunks:
            graph_state["context_text"] = "CTX snapshot=2024-01-01 | DIGEST: none | EVIDENCE: none"
            timings["build_context_text"] = (time.time() - t0) * 1000.0
            return graph_state

        chunks: List[ContextChunk] = []
        for r in retrieved_chunks:
            item: Dict[str, Any] = r.to_json() if hasattr(r, "to_json") else dict(r)
            chunks.append(
                ContextChunk(
                    doc_id=str(item.get("doc_id", "")),
                    paragraph_id=int(item.get("paragraph_id", 0)),
                    chunk_id=int(item.get("chunk_id", 0)),
                    text=str(item.get("text", "")),
                    pages=[int(p) for p in item.get("pages", [])],
                    score=float(item.get("score", 0.0)),
                )
            )

        request: ContextBuilderRequest = ContextBuilderRequest(
            chunks=chunks,
            max_context_chars=max_context_chars,
        )

        result = await self.context_builder_service.build_context(request)

        if not result.success:
            graph_state["context_text"] = "CTX error"
            graph_state["error"] = f"Context building failed: {result.error}"
            timings["build_context_text"] = (time.time() - t0) * 1000.0
            return graph_state

        graph_state["context_text"] = result.context_text
        timings["build_context_text"] = (time.time() - t0) * 1000.0

        logger.info("Context built: {} chars", len(result.context_text))

        return graph_state


