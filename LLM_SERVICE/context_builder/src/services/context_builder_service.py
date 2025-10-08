from __future__ import annotations

from loguru import logger

from src.adapters.vllm_adapter import VLLMAdapter
from src.core.utils import EnvTools
from src.pydantic_schemas.context_builder import (
    ContextBuilderRequest,
    ContextBuilderResponse,
    HealthStatus,
    SummarizerConfig,
)
from src.services.llm_summarizer import LLMSummarizer
from src.services.personality_client import PersonalityClient
from src.services.llm_model import LLMModel


class ContextBuilderService:
    def __init__(self) -> None:
        self.host = EnvTools.required_load_env_var('VLLM_TALKING_HOST')
        self.port = EnvTools.required_load_env_var('VLLM_TALKING_HTTP_PORT')
        self.addr = f"http://{self.host}:{self.port}"
        model_name = EnvTools.required_load_env_var('VLLM_MODEL_NAME')

        adapter = VLLMAdapter(
            base_url=self.addr,
            model_name=model_name,
            timeout=60.0
        )

        llm_model = LLMModel(adapter=adapter)
        personality_client = PersonalityClient(llm_model=llm_model)

        config = SummarizerConfig(model_name=model_name)

        self.llm_summarizer = LLMSummarizer(
            config=config,
            personality_client=personality_client
        )


    async def build_context(
        self,
        request: ContextBuilderRequest
    ) -> ContextBuilderResponse:
        if not request.chunks:
            return ContextBuilderResponse(
                digests=[],
                success=True
            )

        try:
            logger.info(f"Context summarization: {len(request.chunks)} chunks")
            
            digests = await self.llm_summarizer.summarize(
                persona_prompt=request.summarizer_prompt,
                chunks=request.chunks,
                max_chunk_chars=max(0, request.max_context_chars),
            )

            logger.info(
                "Context summarization completed: %s digests",
                len(digests),
            )
            
            return ContextBuilderResponse(
                digests=digests,
                success=True
            )

        except Exception as ex:  # noqa: BLE001
            logger.error(f"Context summarization failed: {ex}")
            return ContextBuilderResponse(
                digests=[],
                success=False,
                error=str(ex)
            )


    def get_health_status(self) -> HealthStatus:
        return HealthStatus(status='healthy')
