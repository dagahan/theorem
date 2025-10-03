from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from src.grpc.client.question_builder_grpc_client import QuestionBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.pydantic_schemas.agent_controller import QuestionBuilderRequest, QuestionBuilderResponse


class QuestionBuilderAdapter:
    def __init__(self) -> None:
        registry = GrpcClientRegistry()
        self.client: QuestionBuilderGrpcClient = registry.register_client(
            'question_builder',
            QuestionBuilderGrpcClient,
        )


    async def process_question(
        self,
        request: QuestionBuilderRequest
    ) -> QuestionBuilderResponse:
        logger.info(f"Starting question processing for: '{request.raw_text}'")
        try:
            response = await self.client.process_question(request)
            logger.info(f"Question processing completed: success={response.success}")
            return response
        except Exception as e:
            logger.error(f"Question processing failed: {e}")
            raise


    async def health_check(self) -> bool:
        return await self.client.health_check()

