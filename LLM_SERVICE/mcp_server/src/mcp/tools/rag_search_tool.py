from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.pydantic_schemas.mcp_server.models import (
    RagSearchInput, RagSearchOutput, DigestItem, SourceChunk,
)

if TYPE_CHECKING:
    from src.adapters.rag_orchestrator_adapter import RagAdapter


class RagSearchTool:
    def __init__(self, rag_adapter: RagAdapter) -> None:
        self.rag_adapter = rag_adapter


    async def execute(
        self,
        search_parameters: RagSearchInput
    ) -> RagSearchOutput:
        logger.info(f"RAG search: q='{search_parameters.query[:80]}...', collection='{search_parameters.collection_name}'")

        response = await self.rag_adapter.rag_search(search_parameters)

        if not response or not getattr(response, "success", True):
            err = getattr(response, "error", "RAG orchestrator error") if response else "empty response"
            return RagSearchOutput(digests=[])

        digests = [
            DigestItem(
                title=d.title,
                summary=d.summary,
                source_chunk=SourceChunk(
                    doc_id=d.source_chunk.doc_id,
                    paragraph_id=d.source_chunk.paragraph_id,
                    chunk_id=d.source_chunk.chunk_id,
                    text=d.source_chunk.text,
                    pages=list(d.source_chunk.pages),
                    score=d.source_chunk.score,
                ),
            )
            for d in response.digests
        ]

        return RagSearchOutput(digests=digests)



