from __future__ import annotations
import os
import time
import uuid
import asyncio
from typing import TYPE_CHECKING, Any, Optional

from loguru import logger

from src.core.utils import EnvTools
from src.domain.models import HealthCheck, UserQuery, QuestionResponse, ServiceStatus
from src.graph.graph_builder import GraphBuilder
from langgraph.checkpoint.memory import MemorySaver

from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.retriever_adapter import RetrieverAdapter
from src.adapters.question_builder_adapter import QuestionBuilderAdapter
from src.adapters.context_builder_adapter import ContextBuilderAdapter
from src.adapters.policy_builder_adapter import PolicyBuilderAdapter

if TYPE_CHECKING:
    from src.domain.models import GraphState


class LLMGraphOrchestrator:
    def __init__(self) -> None:
        self.vllm_adapter = VLLMAdapter()
        self.retriever_adapter = RetrieverAdapter()
        self.question_builder_adapter = QuestionBuilderAdapter()
        self.context_builder_adapter = ContextBuilderAdapter()
        self.policy_builder_adapter = PolicyBuilderAdapter()
        self.default_collection = EnvTools.required_load_env_var("DEFAULT_RETRIEVER_COLLECTION")
        self.max_context_chars = int(float(EnvTools.required_load_env_var("VLLM_TALKING_MAX_LEN")) / 2)
        self.min_results_required = int(EnvTools.required_load_env_var("VLLM_TALKING_MIN_RESULTS"))
        self.checkpointer = MemorySaver()
        self.graph_builder = GraphBuilder(self.vllm_adapter, self.retriever_adapter, self.question_builder_adapter, self.context_builder_adapter, self.policy_builder_adapter)
        self.graph = self.graph_builder.build_graph(self.checkpointer)


    async def answer_question(
        self,
        query: UserQuery,
        run_id: Optional[str] = None,
    ) -> QuestionResponse:
        initial: "GraphState" = {
            "question_id": str(uuid.uuid4()),
            "started_at_ms": time.time() * 1000,
            "timings_ms": {},
            "collection_name": self.default_collection,
            "max_context_chars": self.max_context_chars,
            "min_results_required": self.min_results_required,
            "query": query,
            "success": False,
        }

        state: "GraphState" = await self.graph.ainvoke(
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
            llm_healthy, retriever_healthy, question_builder_healthy, context_builder_healthy, policy_builder_healthy = await asyncio.gather(
                self.vllm_adapter.health_check(),
                self.retriever_adapter.health_check(),
                self.question_builder_adapter.health_check(),
                self.context_builder_adapter.health_check(),
                self.policy_builder_adapter.health_check()
            )

            return HealthCheck(
                overall_status=ServiceStatus.HEALTHY if llm_healthy and retriever_healthy and question_builder_healthy and context_builder_healthy and policy_builder_healthy else ServiceStatus.UNHEALTHY,
                llm_status=ServiceStatus.HEALTHY if llm_healthy else ServiceStatus.UNHEALTHY,
                retriever_status=ServiceStatus.HEALTHY if retriever_healthy else ServiceStatus.UNHEALTHY,
                embedder_status=ServiceStatus.HEALTHY if question_builder_healthy and context_builder_healthy and policy_builder_healthy else ServiceStatus.UNHEALTHY
            )
            
        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return HealthCheck(
                overall_status=ServiceStatus.UNHEALTHY,
                llm_status=ServiceStatus.UNKNOWN,
                retriever_status=ServiceStatus.UNKNOWN,
                embedder_status=ServiceStatus.UNKNOWN
            )




