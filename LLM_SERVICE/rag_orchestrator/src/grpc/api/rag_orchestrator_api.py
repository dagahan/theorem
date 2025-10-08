from __future__ import annotations

import grpc
import grpc.aio  # type: ignore[import-not-found]
from loguru import logger

from protobuf_stubs import rag_orchestrator_pb2 as ro_pb2
from protobuf_stubs import rag_orchestrator_pb2_grpc as ro_grpc
from protobuf_stubs import retriever_pb2 as r_pb2

from src.adapters.retriever_adapter import RetrieverAdapter
from src.adapters.context_builder_adapter import ContextBuilderAdapter


class RagOrchestratorService(ro_grpc.RagOrchestratorServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self.retriever_adapter = RetrieverAdapter()
        self.context_builder_adapter = ContextBuilderAdapter()
        self.use_context_builder = False


    async def Health(
        self,
        request: ro_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,
    ) -> ro_pb2.HealthResponse:
        return ro_pb2.HealthResponse(status="healthy")


    async def Search(
        self,
        request: ro_pb2.RagSearchRequest,
        context: grpc.aio.ServicerContext,
    ) -> ro_pb2.RagSearchResponse:
        try:
            logger.info(f"RAG search request: query='{request.query[:100]}...', collection='{request.collection_name}', top_k={request.top_k}")
            
            retriever_results = await self.retriever_adapter.retrieve(
                question=request.query,
                collection_name=request.collection_name,
                top_k=request.top_k
            )
                
            if not retriever_results:
                logger.warning("Retriever returned no results")
                return ro_pb2.RagSearchResponse(
                    success=False, 
                    error="No results found"
                )

            chunks = []

            for result in retriever_results[:request.top_k]:
                chunks.append(ro_pb2.ContextChunk(
                    doc_id=result.doc_id,
                    paragraph_id=result.paragraph_id,
                    chunk_id=result.chunk_id,
                    text=result.text,
                    pages=result.pages,
                    score=result.score
                ))
                
            if self.use_context_builder:
                digests = await self.context_builder_adapter.build_context(
                    chunks=chunks,
                    max_context_chars=request.max_context_chars,
                    summarizer_prompt=request.summarizer_prompt
                )
                    
                if not digests:
                    logger.error("ContextBuilder returned no digests")
                    return ro_pb2.RagSearchResponse(
                        success=False,
                        error="Context building failed"
                    )

                logger.info(f"RAG search completed: {len(digests)} digests (via context builder)")
            else:
                digests = []
                for chunk in chunks:
                    digest = ro_pb2.DigestItem(
                        title=f"Document {chunk.doc_id}",
                        summary=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                        source_chunk=chunk
                    )
                    digests.append(digest)
                    
                if not digests:
                    logger.error("No digests created")
                    return ro_pb2.RagSearchResponse(
                        success=False,
                        error="No digests created"
                    )

                logger.info(f"RAG search completed: {len(digests)} digests (context builder bypassed)")

            return ro_pb2.RagSearchResponse(
                digests=digests,
                success=True
            )
            
        except grpc.RpcError as ex:
            logger.error(f"gRPC error in RAG search: {ex.code()} - {ex.details()}")
            return ro_pb2.RagSearchResponse(
                success=False,
                error=f"Service error: {ex.details()}"
            )
            
        except Exception as ex:
            logger.error(f"Unexpected error in RAG search: {ex}")
            return ro_pb2.RagSearchResponse(
                success=False,
                error=f"Internal error: {str(ex)}"
            )


