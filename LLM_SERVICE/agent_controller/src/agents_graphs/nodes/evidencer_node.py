from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from src.core.handlers import ResponseHandler
from src.services.llm_model import LLMModel
from src.agents_graphs.graph_tools import GraphTools
from src.pydantic_schemas.agent_controller import ContextDigestItem
from .base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.vllm_adapter import VLLMAdapter


class EvidencerNode(BaseNode):
    def __init__(self, vllm_adapter: "VLLMAdapter") -> None:
        super().__init__('EVIDENCER_NODE_TIMEOUT_SEC', 15.0, 2)
        self.llm = LLMModel(vllm_adapter=vllm_adapter)


    def _get_node_name(self) -> str:
        return 'evidence'


    async def _execute_impl(self, state: "GraphState") -> "GraphState":
        personalities = state.get('personalities')
        if not personalities or 'evidencer' not in personalities.personalities:
            return ResponseHandler.handle_failure(state, "evidencer personality is missing")

        persona = personalities.personalities['evidencer']
        system_prompt = persona.system_prompt

        response_schema = persona.response_schema
        if not response_schema or not isinstance(response_schema, dict):
            return ResponseHandler.handle_failure(state, "evidencer response schema missing or invalid")

        digests_payload = GraphTools.digests_to_payload(state.get('context_digests', []))
        context_payload = {
            "digests": digests_payload
        }
        context = json.dumps(context_payload, ensure_ascii=False)
        question = state.get('question', '')

        result = await self.llm.pydantic_ai_request(
            system_prompt=system_prompt,
            question=question,
            context=context,
            response_schema=response_schema,
            retries=3,
            temperature=0.0,
            max_tokens=1000,
            mcp_server=state.get('mcp_server'),
        )

        if not result or not isinstance(result, dict):
            logger.warning("EVIDENCER: Invalid result from LLM, using original RAG results")
            return ResponseHandler.handle_success(state, 'success')

        condensed_digests = result.get('digests', [])
        
        original_digests = state.get('context_digests', [])
        original_source_map = {
            (d.source_chunk.get('doc_id'), d.source_chunk.get('chunk_id')): d.source_chunk
            for d in original_digests
        }
        
        validated_digests = []
        for digest in condensed_digests:
            source_chunk = digest.get('source_chunk', {})
            
            if isinstance(source_chunk, str):
                logger.warning(f"EVIDENCER: source_chunk is string, skipping digest: {digest.get('title', 'unknown')}")
                continue
                
            doc_id = source_chunk.get('doc_id')
            chunk_id = source_chunk.get('chunk_id')
            
            if (doc_id, chunk_id) in original_source_map:
                validated_digests.append(ContextDigestItem(
                    title=digest.get('title', ''),
                    summary=digest.get('summary', ''),
                    source_chunk=original_source_map[(doc_id, chunk_id)]
                ))
            else:
                logger.warning(f"EVIDENCER: Skipping hallucinated source doc_id={doc_id}, chunk_id={chunk_id}")
        
        if not validated_digests and original_digests:
            logger.warning("EVIDENCER: All digests were hallucinated, using original RAG results")
            validated_digests = [
                ContextDigestItem(
                    title=d.title,
                    summary=d.summary,
                    source_chunk=d.source_chunk
                )
                for d in original_digests
            ]
        
        state['context_digests'] = validated_digests

        logger.info(f"EVIDENCER: Condensed {len(validated_digests)} digests")
        for i, digest in enumerate(validated_digests[:3], 1):  # Show first 3 digests
            title = digest.title[:50] + '...' if len(digest.title) > 50 else digest.title
            summary = digest.summary[:80] + '...' if len(digest.summary) > 80 else digest.summary
            logger.info(f"  Digest {i}: {title} - {summary}")

        state['cycle_summary'] = GraphTools.build_cycle_summary(
            question=question,
            subgoals=(state.get('plan') or {}).get('subgoals', []),
            claims=[],  # No more claims, using context_digests instead
            budgets=state.get('budgets', {}),
            gatekeeper_feedback=state.get('gate_report'),
            context_digests=state.get('context_digests', []),
        )

        return ResponseHandler.handle_success(state, 'success')