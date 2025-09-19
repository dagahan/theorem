from __future__ import annotations

import asyncio
from loguru import logger

from src.domain.models import QuestionBuilderRequest, QuestionBuilderResponse
from src.services.text_normalize_service import TextNormalizeService
from src.services.llm_expansion_service import LLMExpansionService
from src.services.llm_splitting_service import LLMSplittingService


class QuestionBuilderService:
    def __init__(self) -> None:
        self.text_normalizer = TextNormalizeService()
        self.llm_expansion_service = LLMExpansionService()
        self.llm_splitting_service = LLMSplittingService()


    async def process_question(
        self,
        raw_text: str
    ) -> QuestionBuilderResponse:
        try:
            normalized_question = self.text_normalizer.normalize_question_text(raw_text)
            
            if not normalized_question:
                return QuestionBuilderResponse(
                    original_question="",
                    expanded_question="",
                    expanded_question_semantic_parts=[],
                    success=False,
                    error="Empty question after normalization"
                )

            expanded_question = await self.llm_expansion_service.expand_question_for_retriever(normalized_question)

            expanded_question_semantic_parts = await self.llm_splitting_service.split_into_expanded_question_semantic_parts(expanded_question)

            return QuestionBuilderResponse(
                original_question=normalized_question,
                expanded_question=expanded_question,
                expanded_question_semantic_parts=expanded_question_semantic_parts,
                success=True,
                error=None
            )

        except Exception as ex:
            logger.error(f"Question processing failed: {ex}")
            return QuestionBuilderResponse(
                original_question=raw_text,
                expanded_question=raw_text,
                expanded_question_semantic_parts=[raw_text],
                success=False,
                error=str(ex)
            )


