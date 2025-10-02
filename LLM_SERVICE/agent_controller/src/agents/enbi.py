from __future__ import annotations

from functools import partial

from src.domain.models import GraphNodeFactory, StepSpec
from .agent_registry import AgentGraphRegistry


class EnbiAgent:
    NAME = 'enbi' # otsilka :)


    @staticmethod
    def _build_sequence(factory: GraphNodeFactory) -> list[StepSpec]:
        return [
            StepSpec(
                name='build_system_prompt',
                handler=partial(factory.system_prompt_builder_node.execute_node),
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
                name='llm_generation',
                handler=partial(factory.llm_generation_node.execute_node),
                success_key='llm_success',
            ),
        ]


    @classmethod
    def register(cls) -> None:
        AgentGraphRegistry().register(cls.NAME, cls._build_sequence)

