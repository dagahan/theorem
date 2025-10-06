from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents_graphs.nodes.context_builder_node import ContextBuilderNode
    from src.agents_graphs.nodes.response_answer_node import ResponseAnswerNode
    from src.agents_graphs.nodes.question_builder_node import QuestionBuilderNode
    from src.agents_graphs.nodes.retrieval_node import RetrievalNode
    from src.agents_graphs.nodes.personality_builder_node import PersonalityBuilderNode


@dataclass
class GraphNodeFactory:
    personality_builder_node: "PersonalityBuilderNode"
    question_builder_node: "QuestionBuilderNode"
    retrieval_node: "RetrievalNode"
    context_builder_node: "ContextBuilderNode"
    response_answer_node: "ResponseAnswerNode"



    