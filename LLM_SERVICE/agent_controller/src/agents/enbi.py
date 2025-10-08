from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph
from loguru import logger

from src.pydantic_schemas.agent_controller import GraphState, StepSpec
from src.agents_graphs.graph_tools import GraphTools
from .agent_registry import AgentGraphRegistry

from src.agents_graphs.nodes.init_budget_node import InitBudgetNode
from src.agents_graphs.nodes.mcp_init_node import MCPInitNode
from src.agents_graphs.nodes.planner_node import PlannerNode
from src.agents_graphs.nodes.evidencer_node import EvidencerNode
from src.agents_graphs.nodes.gatekeeper_node import GatekeeperNode

if TYPE_CHECKING:
    from src.agents_graphs.graph_node_factory import GraphNodeFactory


class EnbiAgent:
    NAME = 'enbi'


    @staticmethod
    def _build_sequence(factory: GraphNodeFactory) -> list[StepSpec]:
        return [
            StepSpec(
                name='build_personalities',
                handler=partial(factory.personality_builder_node.execute_node),
                success_key='success',
            ),
            StepSpec(
                name='mcp_rag_search',
                handler=partial(factory.mcp_executor_node.execute_node),
                success_key='success',
            ),
            StepSpec(
                name='response_answer',
                handler=partial(factory.response_answer_node.execute_node),
                success_key='response_success',
            ),
        ]


    @staticmethod
    def _build_cot_graph(factory: GraphNodeFactory) -> StateGraph:
        graph = StateGraph(GraphState)

        init_budgets = InitBudgetNode()
        mcp_init = MCPInitNode(factory.mcp_adapter)
        vllm_adapter = factory.response_answer_node.llm_model.vllm_adapter  # type: ignore[attr-defined]
        planner = PlannerNode(vllm_adapter)
        executor = factory.mcp_executor_node
        evidencer = EvidencerNode(vllm_adapter)
        gate = GatekeeperNode(vllm_adapter)
        responder = factory.response_answer_node

        def cot_router(state: GraphState) -> str:
            iter_num = state.get('cot', {}).get('iter', 0)
            max_iters = state.get('budgets', {}).get('max_iters', 1)
            decision = state.get('gate_decision', 'loop')
            
            logger.info(f"COT_ROUTER: iter={iter_num}/{max_iters}, decision={decision}")
            
            if iter_num >= max_iters:
                logger.info(f"COT_ROUTER: EXIT - max_iters reached ({iter_num}/{max_iters})")
                return 'exit'

            if GraphTools.deadline_exceeded(state):
                logger.info(f"COT_ROUTER: EXIT - deadline exceeded")
                return 'exit'

            if decision == 'exit':
                logger.info(f"COT_ROUTER: EXIT - gatekeeper decision")
                return 'exit'

            logger.info(f"COT_ROUTER: LOOP - gatekeeper decision")
            return 'loop'


        graph.add_node('build_personalities', factory.personality_builder_node.execute_node)
        graph.add_node('init_budgets', init_budgets.execute_node)
        graph.add_node('mcp_init', mcp_init.execute_node)
        graph.add_node('plan', planner.execute_node)
        graph.add_node('exec_mcp', executor.execute_node)
        graph.add_node('evidence', evidencer.execute_node)
        graph.add_node('gate', gate.execute_node)
        graph.add_node('responder', responder.execute_node)
        graph.add_node('finalize', factory.finalization_node.execute_node)
        graph.add_node('failure', factory.failure_node.execute_node)

        graph.set_entry_point('build_personalities')

        graph.add_edge('build_personalities', 'init_budgets')
        graph.add_edge('init_budgets', 'mcp_init')
        graph.add_edge('mcp_init', 'plan')

        graph.add_edge('plan', 'exec_mcp')
        graph.add_edge('exec_mcp', 'evidence')
        graph.add_edge('evidence', 'gate')

        graph.add_conditional_edges(
            'gate',
            cot_router,
            {'loop': 'plan', 'exit': 'responder'}
        )

        graph.add_edge('responder', 'finalize')
        graph.add_edge('failure', 'finalize')
        graph.add_edge('finalize', END)

        return graph


    @classmethod
    def register(cls) -> None:
        # AgentGraphRegistry().register(cls.NAME, cls._build_sequence)
        AgentGraphRegistry().register_cot(cls.NAME, cls._build_cot_graph)



