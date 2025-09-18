from __future__ import annotations
from functools import partial
from typing import Any, TYPE_CHECKING

from langgraph.graph import StateGraph, END
from src.domain.models import GraphState

from src.graph.nodes.question_validation_node import QuestionValidationNode
from src.graph.nodes.retrieval_node import RetrievalNode
from src.graph.nodes.context_builder_node import ContextBuilderNode
from src.graph.nodes.llm_generation_node import LLMGenerationNode
from src.graph.nodes.finalization_node import FinalizationNode
from src.graph.nodes.failure_node import FailureNode

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter
    from src.adapters.retriever_adapter import RetrieverAdapter


class GraphBuilder:
    def __init__(self, vllm_adapter_service: "VLLMAdapter", retriever_adapter: "RetrieverAdapter") -> None:
        self.question_validation_node = QuestionValidationNode()
        self.retrieval_node = RetrievalNode(retriever_adapter)
        self.context_builder_node = ContextBuilderNode()
        self.llm_generation_node = LLMGenerationNode(vllm_adapter_service)
        self.finalization_node = FinalizationNode()
        self.failure_node = FailureNode()


    def build_graph(
        self,
        checkpointer: Any
    ) -> Any:
        graph = StateGraph(GraphState)

        graph.add_node("validate_and_prepare", partial(self.question_validation_node.execute_node))
        graph.add_node("retrieve_context", partial(self.retrieval_node.execute_node))
        graph.add_node("build_context_text", partial(self.context_builder_node.execute_node))
        graph.add_node("llm_generation", partial(self.llm_generation_node.execute_node))
        graph.add_node("finalize", partial(self.finalization_node.execute_node))
        graph.add_node("failure", partial(self.failure_node.execute_node))

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
        
        graph.add_edge("build_context_text", "llm_generation")
        graph.add_edge("llm_generation", "finalize")
        graph.add_edge("failure", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile(checkpointer=checkpointer)


    def _route_after_retrieval(
        self,
        graph_state: "GraphState"
    ) -> str:
        return "ok" if graph_state.get("retrieval_success") else "fail"


