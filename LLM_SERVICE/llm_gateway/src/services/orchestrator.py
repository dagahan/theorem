from __future__ import annotations
import os
import time
import uuid
import asyncio
from functools import partial
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, TypeVar, ParamSpec
from typing_extensions import TypedDict
from loguru import logger
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.utils import EnvTools
from src.core.logging import QuestionLogger, ContextRetrievalLogger, LLMGenerationLogger
from src.services.text_normalize_service import TextNormalizeService
from src.domain.models import (
    HealthCheck, QuestionRequest, QuestionResponse, ServiceStatus, RetrieveRequest
)

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

P = ParamSpec("P")
R = TypeVar("R")

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter
    from src.adapters.retriever_adapter import RetrieverAdapter


class _GraphState(TypedDict, total=False):
    question_id: str
    started_at_ms: float
    timings_ms: Dict[str, float]
    collection_name: str
    max_context_chars: int
    min_results_required: int
    request: QuestionRequest
    normalized_question: str
    retrieval_success: bool
    retrieval_error: str
    context_chunks: List[Any]
    context_text: str
    context_guard_passed: bool
    context_guard_reason: str
    llm_answer: str
    llm_success: bool
    llm_error: str
    success: bool
    error: str


def _timeout_and_retry(
    max_attempts: int,
    timeout_sec: float,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def _decor(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        async def _wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=0.2, max=2.0),
                retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
            ):
                with attempt:
                    async with asyncio.timeout(timeout_sec):
                        return await fn(*args, **kwargs)
            raise RuntimeError("unreachable")
        return _wrapped
    return _decor


class LLMGraphOrchestrator:
    def __init__(self, vllm_service: "VLLMAdapter", retriever_service: "RetrieverAdapter") -> None:
        self.llm_service = vllm_service
        self.retriever_service = retriever_service
        self.default_collection = EnvTools.required_load_env_var("DEFAULT_RAG_COLLECTION")
        self.max_context_chars = int(os.getenv("LLM_GATEWAY_MAX_CONTEXT_CHARS", "8000"))
        self.min_results_required = int(os.getenv("LLM_GATEWAY_MIN_RESULTS", "1"))
        self._text_norm = TextNormalizeService()

        self._checkpointer = MemorySaver()

        self._graph = self._build_graph()


    def _build_graph(self) -> Any:
        graph = StateGraph(_GraphState)

        graph.add_node("validate_and_prepare", partial(self._node_validate_and_prepare))
        graph.add_node("retrieve_context", partial(self._node_retrieve_context))
        graph.add_node("build_context_text", partial(self._node_build_context_text))
        graph.add_node("guard_context_quality", partial(self._node_guard_context_quality))
        graph.add_node("llm_generation", partial(self._node_llm_generation))
        graph.add_node("finalize", partial(self._node_finalize))
        graph.add_node("failure", partial(self._node_failure))

        graph.set_entry_point("validate_and_prepare")
        graph.add_edge("validate_and_prepare", "retrieve_context")

        graph.add_conditional_edges(
            "retrieve_context",
            partial(self._route_after_retrieval),
            {
                "ok": "build_context_text",
                "fail": "failure",
            },
        )
        
        graph.add_edge("build_context_text", "guard_context_quality")
        graph.add_edge("guard_context_quality", "llm_generation")
        graph.add_edge("llm_generation", "finalize")
        graph.add_edge("failure", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile(checkpointer=self._checkpointer)


    async def answer_question(
        self,
        request: QuestionRequest,
        run_id: Optional[str] = None,
    ) -> QuestionResponse:
        initial: _GraphState = {
            "question_id": str(uuid.uuid4()),
            "started_at_ms": time.time() * 1000,
            "timings_ms": {},
            "collection_name": self.default_collection,
            "max_context_chars": self.max_context_chars,
            "min_results_required": self.min_results_required,
            "request": request,
            "success": False,
        }

        state: _GraphState = await self._graph.ainvoke(
            initial,
            config={"configurable": {"thread_id": run_id or initial["question_id"]}}
        )

        return QuestionResponse(
            answer=state.get("llm_answer", ""),
            success=state.get("success", False),
            error=state.get("error", "")
        )


    async def health_check(self) -> HealthCheck:
        try:
            llm_healthy, retriever_healthy = await asyncio.gather(
                self.llm_service.health_check(),
                self.retriever_service.health_check()
            )
            return HealthCheck(
                overall_status=ServiceStatus.HEALTHY if llm_healthy and retriever_healthy else ServiceStatus.UNHEALTHY,
                llm_status=ServiceStatus.HEALTHY if llm_healthy else ServiceStatus.UNHEALTHY,
                retriever_status=ServiceStatus.HEALTHY if retriever_healthy else ServiceStatus.UNHEALTHY,
                embedder_status=ServiceStatus.HEALTHY
            )
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return HealthCheck(
                overall_status=ServiceStatus.UNHEALTHY,
                llm_status=ServiceStatus.UNKNOWN,
                retriever_status=ServiceStatus.UNKNOWN,
                embedder_status=ServiceStatus.UNKNOWN
            )


    async def _node_validate_and_prepare(
        self,
        state: _GraphState
    ) -> _GraphState:
        t0 = time.time()
        req = state["request"]

        if not req.question or not req.question.strip():
            state["success"] = False
            state["error"] = "Question is empty."
            return state

        normalized = self._text_norm.normalize_query_text(req.question)
        state["normalized_question"] = normalized

        state["timings_ms"]["validate_and_prepare"] = (time.time() - t0) * 1000
        return state


    @_timeout_and_retry(max_attempts=3, timeout_sec=25.0)
    async def _node_retrieve_context(
        self,
        state: _GraphState
    ) -> _GraphState:
        t0 = time.time()
        req = state["request"]
        qid = state["question_id"]
        collection = state["collection_name"]

        retrieve_request = RetrieveRequest(query=req.question, collection_name=collection)
        response = await self.retriever_service.retrieve_context(retrieve_request)

        state["retrieval_success"] = bool(response.success and response.results)
        state["retrieval_error"] = response.error or ""
        state["context_chunks"] = response.results if response.success else []

        elapsed = (time.time() - t0) * 1000
        state["timings_ms"]["retrieve_context"] = elapsed

        ContextRetrievalLogger.log_context_retrieval(
            question_id=qid,
            query=req.question,
            retrieved_chunks=[c.to_json() for c in (response.results or [])] if response.success else [],
            retrieval_time_ms=elapsed,
            success=response.success,
            error_message=response.error or ""
        )

        return state


    async def _node_build_context_text(
        self,
        state: _GraphState
    ) -> _GraphState:
        t0 = time.time()
        chunks = state.get("context_chunks", [])
        max_chars = state["max_context_chars"]

        if not chunks:
            state["context_text"] = "Контекст не найден."
            state["timings_ms"]["build_context_text"] = (time.time() - t0) * 1000
            return state

        parts: List[str] = []
        used = 0
        for i, r in enumerate(chunks, 1):
            text = getattr(r, 'text', '')
            doc_id = getattr(r, 'doc_id', 'unknown')
            pages = getattr(r, 'pages', [])
            score = getattr(r, 'score', 0.0)
            
            header = f"{i}. doc={doc_id}, pages={pages}, score={score:.3f}"
            if used + len(header) + 1 > max_chars:
                break
                
            remaining_chars = max_chars - used - len(header) - 1
            if remaining_chars > 0:
                truncated_text = text[:remaining_chars] if len(text) > remaining_chars else text
                line = f"{header}\n{truncated_text}"
            else:
                line = header
                
            parts.append(line)
            used += len(line) + 1

        state["context_text"] = "\n".join(parts) if parts else "Контекст не найден."
        state["timings_ms"]["build_context_text"] = (time.time() - t0) * 1000
        return state


    async def _node_guard_context_quality(
        self,
        state: _GraphState
    ) -> _GraphState:
        t0 = time.time()
        chunks = state.get("context_chunks", [])
        min_required = state["min_results_required"]

        if not chunks or len(chunks) < min_required:
            state["context_guard_passed"] = False
            state["context_guard_reason"] = f"Not enough chunks ({len(chunks) if chunks else 0})"
        else:
            try:
                scores = [float(getattr(c, "score", 0.0)) for c in chunks]
                guard_ok = sum(scores) / max(1, len(scores)) > 0.0
            except Exception:
                guard_ok = True

            state["context_guard_passed"] = guard_ok
            state["context_guard_reason"] = "" if guard_ok else "Average score ≤ 0.0"

        state["timings_ms"]["guard_context_quality"] = (time.time() - t0) * 1000
        
        if not state.get("context_guard_passed", True):
            reason = state.get("context_guard_reason", "unknown")
            logger.warning(f"Context guard not passed: {reason}")
        
        return state


    @_timeout_and_retry(max_attempts=3, timeout_sec=60.0)
    async def _node_llm_generation(
        self,
        state: _GraphState
    ) -> _GraphState:
        t0 = time.time()
        req = state["request"]
        qid = state["question_id"]
        ctx = state.get("context_text", "")

        llm = await self.llm_service.generate_answer(
            req.question,
            ctx,
            req.stream
        )

        state["llm_answer"] = llm.answer or ""
        state["llm_success"] = bool(llm.success)
        state["llm_error"] = llm.error or ""

        elapsed = (time.time() - t0) * 1000
        state["timings_ms"]["llm_generation"] = elapsed

        LLMGenerationLogger.log_llm_generation(
            question_id=qid,
            question=req.question,
            context=ctx,
            llm_response=llm.answer,
            generation_time_ms=elapsed,
            success=llm.success,
            error_message=llm.error or ""
        )

        return state


    async def _node_finalize(
        self,
        state: _GraphState
    ) -> _GraphState:
        total_ms = (time.time() * 1000) - state.get("started_at_ms", time.time() * 1000)
        state["success"] = bool(state.get("llm_success", False))
        state["error"] = "" if state["success"] else (state.get("llm_error") or state.get("retrieval_error") or "Unknown error")

        QuestionLogger.log_question_processing(
            question_id=state["question_id"],
            original_question=state["request"].question,
            context_chunks=[c.to_json() for c in state.get("context_chunks", [])],
            llm_response=state.get("llm_answer", ""),
            processing_time_ms=total_ms,
            success=state["success"],
            error_message=state["error"]
        )

        return state


    async def _node_failure(
        self,
        state: _GraphState
    ) -> _GraphState:
        state["success"] = False
        state["error"] = state.get("retrieval_error", "Context retrieval failed")

        total_ms = (time.time() * 1000) - state.get("started_at_ms", time.time() * 1000)
        QuestionLogger.log_question_processing(
            question_id=state["question_id"],
            original_question=state["request"].question,
            context_chunks=[],
            llm_response="",
            processing_time_ms=total_ms,
            success=False,
            error_message=state["error"]
        )

        return state


    def _route_after_retrieval(
        self,
        state: _GraphState
    ) -> str:
        return "ok" if state.get("retrieval_success") else "fail"


