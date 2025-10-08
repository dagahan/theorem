from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents_graphs.nodes.base_node import BaseNode
    from src.agents_graphs.nodes.finalization_node import FinalizationNode
    from src.agents_graphs.nodes.failure_node import FailureNode
    from src.adapters.mcp_adapter import MCPAdapter


@dataclass
class GraphNodeFactory:
    personality_builder_node: "BaseNode"
    response_answer_node: "BaseNode"
    mcp_executor_node: "BaseNode"
    mcp_adapter: "MCPAdapter"
    finalization_node: "FinalizationNode"
    failure_node: "FailureNode"



    