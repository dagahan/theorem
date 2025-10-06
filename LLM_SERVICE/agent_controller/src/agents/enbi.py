from __future__ import annotations

from functools import partial

from src.pydantic_schemas.agent_controller import StepSpec
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents_graphs.graph_node_factory import GraphNodeFactory
from .agent_registry import AgentGraphRegistry


class EnbiAgent:
    NAME = 'enbi' # otsilka :)


    @staticmethod
    def _build_sequence(factory: GraphNodeFactory) -> list[StepSpec]:
        return [
            StepSpec(
                name='build_personalities',
                handler=partial(factory.personality_builder_node.execute_node),
                success_key='success',
            ),
            StepSpec(
                name='build_question',
                handler=partial(factory.question_builder_node.execute_node),
                success_key='success',
            ),
            StepSpec(
                name='retrieve_context',
                handler=partial(factory.retrieval_node.execute_node),
                success_key='retrieval_success',
            ),
            StepSpec(
                name='build_context_text',
                handler=partial(factory.context_builder_node.execute_node),
                success_key='success',
            ),
            StepSpec(
                name='response_answer',
                handler=partial(factory.response_answer_node.execute_node),
                success_key='llm_success',
            ),
        ]


    @classmethod
    def register(cls) -> None:
        AgentGraphRegistry().register(cls.NAME, cls._build_sequence)

