from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, TYPE_CHECKING, Callable, Coroutine
from loguru import logger

if TYPE_CHECKING:
    import grpc

from protobuf_stubs import question_builder_pb2, question_builder_pb2_grpc
from src.grpc.grpc_utils import GrpcTools
from src.services.question_builder_service import QuestionBuilderService
from src.services.health_service import HealthService


grpc_tools = GrpcTools()


class QuestionBuilderAPI(question_builder_pb2_grpc.QuestionBuilderServiceServicer):  # type: ignore[misc]
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop_forever, args=(self._loop,), name="question-builder-async-loop", daemon=True).start()
        self._run: Callable[[Coroutine[Any, Any, Any]], Any] = lambda coro: asyncio.run_coroutine_threadsafe(coro, self._loop).result()
        
        self.question_builder_service = QuestionBuilderService()
        self.health_checker = HealthService()


    @staticmethod
    def _loop_forever(loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()


    @grpc_tools.log_grpc_request("Health")
    def Health(self, request: question_builder_pb2.HealthRequest, context: grpc.ServicerContext) -> question_builder_pb2.HealthResponse:
        try:
            grpc_tools.validate_proto(request, context)

            llm_status, _ = self._run(
                self.health_checker.health_check_service("all")
            )

            overall = "healthy" if llm_status == "healthy" else "unhealthy"

            response = question_builder_pb2.HealthResponse(
                status=overall,
                llm_status=llm_status,
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:
            logger.error(f"Health check failed: {ex}")
            return question_builder_pb2.HealthResponse(
                status="unhealthy",
                llm_status="unknown"
            )


    @grpc_tools.log_grpc_request("ProcessQuestion")
    def ProcessQuestion(self, request: question_builder_pb2.ProcessQuestionRequest, context: grpc.ServicerContext) -> question_builder_pb2.ProcessQuestionResponse:
        try:
            grpc_tools.validate_proto(request, context)

            result = self._run(
                self.question_builder_service.process_question(request.raw_text)
            )

            response = question_builder_pb2.ProcessQuestionResponse(
                original_question=result.original_question,
                expanded_question=result.expanded_question,
                expanded_question_semantic_parts=result.expanded_question_semantic_parts,
                success=result.success,
                error=result.error
            )

            grpc_tools.validate_proto(response, context)

            return response

        except Exception as ex:
            logger.exception("ProcessQuestion failed")
            return question_builder_pb2.ProcessQuestionResponse(
                original_question="",
                expanded_question="",
                expanded_question_semantic_parts=[],
                success=False,
                error=str(ex)
            )



