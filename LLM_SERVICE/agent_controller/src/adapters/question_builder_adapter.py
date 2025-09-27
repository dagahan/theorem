from __future__ import annotations

from typing import TYPE_CHECKING

from src.grpc.client.question_builder_grpc_client import QuestionBuilderGrpcClient
from src.grpc.client.registry_grpc_clients import GrpcClientRegistry

if TYPE_CHECKING:
    from src.domain.models import QuestionBuilderRequest, QuestionBuilderResponse


class QuestionBuilderAdapter:
    def __init__(self) -> None:
        self.client: QuestionBuilderGrpcClient = GrpcClientRegistry().register_client("question_builder", QuestionBuilderGrpcClient)


    async def process_question(
        self,
        request: QuestionBuilderRequest
    ) -> QuestionBuilderResponse:
        return await self.client.process_question(request)


    async def health_check(self) -> bool:
        return await self.client.health_check()


