from __future__ import annotations

from typing import TYPE_CHECKING
from src.pydantic_schemas.agent_controller import ContextDigestItem, ContextChunk

from loguru import logger

from src.agents_graphs.graph_tools import GraphTools
from src.core.handlers import ResponseHandler
from src.pydantic_schemas.mcp_server.models import RagSearchInput
from src.agents_graphs.nodes.base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.mcp_adapter import MCPAdapter


class MCPExecutorNode(BaseNode):
    def __init__(self, adapter: "MCPAdapter") -> None:
        super().__init__("MCP_EXECUTOR_TIMEOUT_SEC", 90.0, 3)
        self.adapter = adapter


    def _get_node_name(self) -> str:
        return "mcp_executor"


    async def _execute_impl(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        await self.adapter.ensure_catalog_in_state(graph_state)
        
        mcp_data = graph_state.get("mcp", {})

        graph_state["mcp_tools"] = mcp_data.get("catalog", {}).get("tools", {})
        graph_state["mcp_schemas"] = mcp_data.get("compiled", {})

        query = graph_state.get("rag_query", "") or graph_state.get("question") or graph_state["query"].raw_text

        collection_name = graph_state.get("rag_collection", graph_state.get("collection_name", "fipi_documents"))
        top_k_raw = graph_state.get("rag_top_k", 6)
        top_k = int(top_k_raw) if isinstance(top_k_raw, (int, str)) else 6

        max_context_chars = int(graph_state.get("max_context_chars", GraphTools.resolve_default_max_context_chars()) or GraphTools.resolve_default_max_context_chars())

        summarizer_prompt = graph_state.get("rag_summarizer_prompt", "Summarize into key points, concisely")

        if not query:
            graph_state["context_digests"] = []
            return ResponseHandler.handle_success(graph_state, "success")

        params = RagSearchInput(
            query=query,
            collection_name=str(collection_name),
            top_k=top_k,
            max_context_chars=max_context_chars,
            summarizer_prompt=str(summarizer_prompt),
        )

        try:
            result = await self.adapter.rag_search(params)
            logger.info(f"MCP rag.search result: {len(result.digests)} digests")

        except Exception as ex:
            logger.error(f"MCP rag.search failed: {ex}")
            graph_state["context_digests"] = []
            
            return ResponseHandler.handle_failure(
                graph_state,
                f"MCP rag.search failed: {ex}",
                additional_data={"mcp_rag_error": str(ex)},
                error_key="success",
            )

        context_digests = []

        for digest in result.digests:
            context_chunk = ContextChunk(
                doc_id=digest.source_chunk.doc_id,
                paragraph_id=digest.source_chunk.paragraph_id,
                chunk_id=digest.source_chunk.chunk_id,
                text=digest.source_chunk.text,
                pages=digest.source_chunk.pages,
                score=digest.source_chunk.score,
            )

            context_digest = ContextDigestItem(
                title=digest.title,
                summary=digest.summary,
                source_chunk=context_chunk,
            )

            context_digests.append(context_digest)

        graph_state["context_digests"] = context_digests

        logger.info(f"MCP rag.search -> {len(context_digests)} digests")
        
        return ResponseHandler.handle_success(
            graph_state,
            "success",
            additional_data={"mcp_rag_error": ""},
        )



