from __future__ import annotations

from loguru import logger

from src.grpc.client.rag_orchestrator_grpc_client import RagOrchestratorGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry
from src.pydantic_schemas.mcp_server.models import (
    RagSearchInput, RagSearchOutput, DigestItem, SourceChunk,
)


class RagAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: RagOrchestratorGrpcClient = registry.register_client(
            "rag_orchestrator",
            RagOrchestratorGrpcClient,
        )


    async def health_check(self) -> bool:
        return await self.client.health_check()


    async def rag_search(
        self,
        params: RagSearchInput
    ) -> RagSearchOutput:
        logger.info(f"RAG search: q='{params.query[:80]}...', collection='{params.collection_name}'")

        response = await self.client.rag_search(
            query=params.query,
            collection_name=params.collection_name,
            top_k=params.top_k,
            max_context_chars=params.max_context_chars,
            summarizer_prompt=params.summarizer_prompt,
        )

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


