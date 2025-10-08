from __future__ import annotations

from typing import TYPE_CHECKING
from src.pydantic_schemas.agent_controller import ContextDigestItem

from loguru import logger

from src.agents_graphs.graph_tools import GraphTools
from src.core.handlers import ResponseHandler
from src.pydantic_schemas.mcp_server.models import RagSearchInput
from src.agents_graphs.nodes.base_node import BaseNode

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import GraphState
    from src.adapters.mcp_adapter import MCPAdapter


class MCPExecutorNode(BaseNode):
    def __init__(self, mcp_adapter: "MCPAdapter") -> None:
        super().__init__("MCP_EXECUTOR_TIMEOUT_SEC", 90.0, 3)
        self.mcp_adapter = mcp_adapter


    def _get_node_name(self) -> str:
        return "mcp_executor"


    async def _execute_impl(
        self,
        graph_state: "GraphState"
    ) -> "GraphState":
        plan = graph_state.get("plan")
        
        logger.info(f"EXECUTOR: Plan state: {plan}")

        if plan and isinstance(plan, dict) and plan.get("actions"):
            logger.info(f"EXECUTOR: Executing {len(plan['actions'])} actions from plan")
            merged_digests = []
            for i, action in enumerate(plan["actions"], 1):
                try:
                    if action.get("tool") == "rag.search":
                        query = str(action.get("args", {}).get("query", graph_state.get("question", "")))
                        collection = str(graph_state.get("rag_collection", graph_state.get("collection_name", "fipi_documents")))
                        logger.info(f"  Action {i}: Searching RAG - '{query}' in {collection}")
                        
                        params = RagSearchInput(
                            query=query,
                            collection_name=collection,
                            top_k=int(action.get("args", {}).get("top_k", graph_state.get("rag_top_k", 6))),
                            max_context_chars=GraphTools.resolve_default_max_context_chars(),
                            summarizer_prompt=str(graph_state.get("rag_summarizer_prompt", "Summarize into key points, concisely")),
                        )

                        result = await self.mcp_adapter.rag_search(params)
                        for digest in result.digests:
                            source_chunk_dict = digest.source_chunk.model_dump() if hasattr(digest.source_chunk, 'model_dump') else digest.source_chunk
                            merged_digests.append(
                                ContextDigestItem(
                                    title=digest.title,
                                    summary=digest.summary,
                                    source_chunk=source_chunk_dict,
                                )
                            )
                        logger.info(f"    Found {len(result.digests)} documents")
                except Exception as ex:
                    logger.error(f"  Action {i}: Error executing {action.get('id', 'unknown')}: {ex}")

            if merged_digests:
                graph_state["context_digests"] = merged_digests
                logger.info(f"EXECUTOR: Collected {len(merged_digests)} total documents")
                return ResponseHandler.handle_success(
                    graph_state, "success", additional_data={"mcp_rag_error": ""}
                )

        logger.info("EXECUTOR: No plan actions found - skipping execution")
        graph_state["context_digests"] = []
        return ResponseHandler.handle_success(graph_state, "EXECUTOR: No plan to execute")



