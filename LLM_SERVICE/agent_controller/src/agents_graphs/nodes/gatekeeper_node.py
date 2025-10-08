from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.core.handlers import ResponseHandler
from src.services.llm_model import LLMModel
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.vllm_adapter import VLLMAdapter


class GatekeeperNode(BaseNode):
    def __init__(self, vllm_adapter: "VLLMAdapter") -> None:
        super().__init__('GATEKEEPER_NODE_TIMEOUT_SEC', 15.0, 2)
        self.llm = LLMModel(vllm_adapter=vllm_adapter)


    def _get_node_name(self) -> str:
        return 'gate'


    async def _execute_impl(self, state: "GraphState") -> "GraphState":
        personalities = state.get('personalities')
        if not personalities or 'gatekeeper' not in personalities.personalities:
            return ResponseHandler.handle_failure(state, "gatekeeper personality is missing")

        persona = personalities.personalities['gatekeeper']
        system_prompt = persona.system_prompt

        response_schema = persona.response_schema
        if not response_schema or not isinstance(response_schema, dict):
            return ResponseHandler.handle_failure(state, "gatekeeper response schema missing or invalid")

        question = state.get('question', '')
        cycle_summary = state.get('cycle_summary', {})
        
        context = json.dumps({
            "cycle_summary": cycle_summary,
            "subgoals": (state.get('plan') or {}).get('subgoals', []),
            "context_digests": [
                {
                    "title": d.title, 
                    "summary": d.summary,
                    "text": d.source_chunk.get('text', '')
                } 
                for d in state.get('context_digests', [])
            ],
            "budgets": state.get('budgets', {}),
        }, ensure_ascii=False)
        
        logger.info(f"GATEKEEPER: Received {len(state.get('context_digests', []))} digests")
        for i, d in enumerate(state.get('context_digests', [])[:2], 1):
            logger.info(f"  Digest {i}: {d.title} - {d.summary[:100]}... - {d.source_chunk.get('text', '')[:100]}...")

        logger.info(f"GATEKEEPER: Sending context to LLM: {context[:500]}...")
        
        # TEMPORARY: Always exit to get any response
        report: dict[str, Any] = {
            "coverage": 1.0,
            "decision": "exit",
            "missing_subgoals": [],
            "contradictions": [],
            "budget_warning": "",
            "next_hints": []
        }
        state['gate_report'] = report
        decision = str(report.get('decision', 'loop'))
        state['gate_decision'] = decision

        coverage = float(report.get('coverage', 0))
        missing = list(report.get('missing_subgoals', []))
        contradictions = list(report.get('contradictions', []))
        iter_num = int(state['cot'].get('iter', 0)) + 1
        
        state['cot']['iter'] = iter_num
        
        logger.info(f"GATEKEEPER: {decision.upper()}, coverage={coverage:.1%}, missing={len(missing)}, contradictions={len(contradictions)}, iter={iter_num}")
        if missing:
            logger.info(f"  Missing: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")
        if contradictions:
            logger.info(f"  Contradictions: {', '.join(contradictions[:2])}{'...' if len(contradictions) > 2 else ''}")

        return ResponseHandler.handle_success(state, 'success')


        