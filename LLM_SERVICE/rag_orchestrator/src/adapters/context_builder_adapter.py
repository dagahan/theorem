from __future__ import annotations

from typing import Any, List
from loguru import logger

from src.grpc.client.context_builder_grpc_client import ContextBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry


class ContextBuilderAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: ContextBuilderGrpcClient = registry.register_client(
            "context_builder",
            ContextBuilderGrpcClient,
        )

    async def build_context(
        self,
        chunks: List[Any],
        max_context_chars: int,
        summarizer_prompt: str
    ) -> List[Any]:
        logger.info(f"ContextBuilder: {len(chunks)} chunks, max_chars={max_context_chars}")
        
        response = await self.client.build_context(
            chunks=chunks,
            max_context_chars=max_context_chars,
            summarizer_prompt=summarizer_prompt
        )

        if not response.success:
            logger.error(f"ContextBuilder failed: {response.error}")
            return []

        logger.info(f"ContextBuilder returned {len(response.digests)} digests")
        return response.digests  # type: ignore[no-any-return]