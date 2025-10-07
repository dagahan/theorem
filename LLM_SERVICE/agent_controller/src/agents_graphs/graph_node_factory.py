from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents_graphs.nodes.base_node import BaseNode


@dataclass
class GraphNodeFactory:
    personality_builder_node: "BaseNode"
    retrieval_node: "BaseNode"
    context_builder_node: "BaseNode"
    response_answer_node: "BaseNode"
    mcp_executor_node: "BaseNode"



    