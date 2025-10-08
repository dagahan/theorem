import inspect
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger
from src.core.utils import FileSystemTools
from src.pydantic_schemas.agent_controller import ContextDigestItem


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        log_level: int
        try:
            log_level = logger.level(record.levelname).no
        except ValueError:
            log_level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and depth < 10:
            if frame.f_code.co_filename == logging.__file__:
                depth += 1
            frame = frame.f_back

        logger.opt(depth=depth, exception=record.exc_info, record=True).log(
            log_level, record.getMessage()
        )


class LogSetup:
    @staticmethod
    def configure() -> None:
        logger.remove()
        logger.add(
            "debug/debug.json",
            format="{time} {level} {message}",
            serialize=True,
            rotation="04:00",
            retention="14 days",
            compression="zip",
            level="DEBUG",
            catch=True,
        )

        logger.add(
            sys.stdout,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}",
            level="DEBUG",
            catch=True,
        )


class QuestionLogger:
    @staticmethod
    def log_question_processing(
        question_id: str,
        question: str,
        response_answer: str,
        processing_time_ms: float,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/question_processing"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{question_id}.json")
            
            question_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "question_id": question_id,
                "question": question,
                "response_answer": response_answer,
                "success": success,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "question_id": question_id,
                "question_processing": [question_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log question processing results: {ex}")


class ContextRetrievalLogger:
    @staticmethod
    def log_context_retrieval(
        question_id: str,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        retrieval_time_ms: float,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/context_retrieval"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{question_id}.json")
            
            retrieval_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "question_id": question_id,
                "query": query,
                "retrieved_chunks": [
                    {
                        "doc_id": chunk.get("doc_id", ""),
                        "paragraph_id": chunk.get("paragraph_id", 0),
                        "chunk_id": chunk.get("chunk_id", 0),
                        "score": chunk.get("score", 0.0),
                        "pages": chunk.get("pages", []),
                        "text": chunk.get("text", "")
                    }
                    
                    for chunk in retrieved_chunks
                ],
                "success": success,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "question_id": question_id,
                "context_retrieval": [retrieval_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log context retrieval results: {ex}")


class ResponderGenerationLogger:
    @staticmethod
    def log_responder_generation(
        question_id: str,
        question: str,
        context: str,
        response_answer: str,
        generation_time_ms: float,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/llm_generation"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{question_id}.json")
            
            generation_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "question_id": question_id,
                "question": question,
                "context": context,
                "response_answer": response_answer,
                "success": success,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "question_id": question_id,
                "llm_generation": [generation_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log LLM generation results: {ex}")


class QuestionBuilderLogger:
    @staticmethod
    def log_question_building(
        question_id: str,
        question: str,
        building_time_ms: float,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/question_building"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{question_id}.json")
            
            building_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "question_id": question_id,
                "question": question,
                "success": success,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "question_id": question_id,
                "question_building": [building_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log question building results: {ex}")


class ContextBuilderLogger:
    @staticmethod
    def log_context_building(
        question_id: str,
        input_chunks_count: int,
        digests: List[ContextDigestItem],
        building_time_ms: float,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/context_building"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{question_id}.json")
            
            serialized_digests = [
                {
                    "title": digest.title,
                    "summary": digest.summary,
                    "source_chunk": digest.source_chunk,
                }
                for digest in digests
            ]

            building_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "question_id": question_id,
                "digests": serialized_digests,
                "success": success,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "question_id": question_id,
                "context_building": [building_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log context building results: {ex}")


class PersonalityBuilderLogger:
    @staticmethod
    def log_personality_building(
        question_id: str,
        personalities: Any,  # Personalities object
        building_time_ms: float,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/personality_building"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{question_id}.json")
            
            # Convert Personalities object to dict for JSON serialization
            personalities_dict = {}
            if hasattr(personalities, 'personalities'):
                for name, personality in personalities.personalities.items():
                    personalities_dict[name] = {
                        "name": personality.name,
                        "system_prompt": personality.system_prompt,
                        "response_schema": personality.response_schema.get("fingerprint") if personality.response_schema else None
                    }
            
            building_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "question_id": question_id,
                "personalities": personalities_dict,
                "success": success,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "question_id": question_id,
                "personality_building": [building_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log personality building results: {ex}")

