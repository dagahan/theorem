from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from langgraph.graph import END, StateGraph

from src.agents.agent_registry import AgentGraphRegistry
from src.pydantic_schemas.agent_controller import InferenceParams, Personality
from .graph_node_factory import GraphNodeFactory
from .nodes.context_builder_node import ContextBuilderNode
from .nodes.failure_node import FailureNode
from .nodes.finalization_node import FinalizationNode
from .nodes.response_answer_node import ResponseAnswerNode
from .nodes.question_builder_node import QuestionBuilderNode
from .nodes.retrieval_node import RetrievalNode
from .nodes.personality_builder_node import PersonalityBuilderNode

if TYPE_CHECKING:
    from src.adapters.context_builder_adapter import ContextBuilderAdapter
    from src.adapters.question_builder_adapter import QuestionBuilderAdapter
    from src.adapters.retriever_adapter import RetrieverAdapter
    from src.adapters.personality_builder_adapter import PersonalityBuilderAdapter
    from src.adapters.vllm_adapter import VLLMAdapter

from src.pydantic_schemas.agent_controller import GraphState


class GraphBuilder:
    def __init__(
        self,
        vllm_adapter_service: 'VLLMAdapter',
        retriever_adapter: 'RetrieverAdapter',
        question_builder_adapter: 'QuestionBuilderAdapter',
        context_builder_adapter: 'ContextBuilderAdapter',
        personality_builder_adapter: 'PersonalityBuilderAdapter',
    ) -> None:
        self.question_builder_node = QuestionBuilderNode(question_builder_adapter)
        self.retrieval_node = RetrievalNode(retriever_adapter)
        self.context_builder_node = ContextBuilderNode(context_builder_adapter)
        self.personality_builder_node = PersonalityBuilderNode(personality_builder_adapter)
        self.response_answer_node = ResponseAnswerNode(
            vllm_adapter=vllm_adapter_service,
            defaults=InferenceParams()
        )
        self.finalization_node = FinalizationNode()
        self.failure_node = FailureNode()

        self.agent_graph_registry = AgentGraphRegistry()
        self.graph_node_factory = GraphNodeFactory(
            personality_builder_node=self.personality_builder_node,
            question_builder_node=self.question_builder_node,
            retrieval_node=self.retrieval_node,
            context_builder_node=self.context_builder_node,
            response_answer_node=self.response_answer_node,
        )


    def build_graph(
        self,
        agent_name: str,
        checkpointer: Any,
    ) -> Any:
        factory = self.agent_graph_registry.get(agent_name)
        sequence = factory(self.graph_node_factory)

        if not sequence:
            raise ValueError(f"Agent '{agent_name}' returned empty step sequence")

        graph = StateGraph(GraphState)

        for step in sequence:
            graph.add_node(step.name, step.handler)

        graph.add_node('finalize', partial(self.finalization_node.execute_node))
        graph.add_node('failure', partial(self.failure_node.execute_node))

        graph.set_entry_point(sequence[0].name)

        for index, step in enumerate(sequence):
            next_step = sequence[index + 1].name if index + 1 < len(sequence) else 'finalize'
            graph.add_conditional_edges(
                step.name,
                self._make_router(step.success_key),
                {'ok': next_step, 'fail': step.on_fail},
            )

        graph.add_edge('failure', 'finalize')
        graph.add_edge('finalize', END)

        return graph.compile(checkpointer=checkpointer)


    @staticmethod
    def _make_router(success_key: str) -> Callable[[GraphState], str]:
        def router(state: GraphState) -> str:
            return 'ok' if bool(state.get(success_key, True)) else 'fail'

        return router
