import inspect
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger
from src.core.utils import FileSystemTools


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
        original_question: str,
        context_chunks: List[Dict[str, Any]],
        llm_response: str,
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
                "original_question": original_question,
                "question_length": len(original_question),
                "context_chunks_count": len(context_chunks),
                "context_chunks": [
                    {
                        "doc_id": chunk.get("doc_id", ""),
                        "paragraph_id": chunk.get("paragraph_id", 0),
                        "chunk_id": chunk.get("chunk_id", 0),
                        "score": chunk.get("score", 0.0),
                        "pages": chunk.get("pages", []),
                        "text": chunk.get("text", "")
                    }

                    for chunk in context_chunks
                ],
                "llm_response": llm_response,
                "llm_response_length": len(llm_response),
                "processing_time_ms": processing_time_ms,
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
            
            logger.debug(f"Question processing logged for {question_id}: {len(context_chunks)} chunks, {processing_time_ms:.2f}ms")
            logger.debug(f"Question processing results logged to debug log file: {file_path} for question_id: {question_id}")
            
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
                "query_length": len(query),
                "retrieved_chunks_count": len(retrieved_chunks),
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
                "retrieval_time_ms": retrieval_time_ms,
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
            
            logger.debug(f"Context retrieval logged for {question_id}: {len(retrieved_chunks)} chunks, {retrieval_time_ms:.2f}ms")
            logger.debug(f"Context retrieval results logged to debug log file: {file_path} for question_id: {question_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log context retrieval results: {ex}")


class LLMGenerationLogger:
    @staticmethod
    def log_llm_generation(
        question_id: str,
        question: str,
        context: str,
        llm_response: str,
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
                "question_length": len(question),
                "context": context,
                "context_length": len(context),
                "llm_response": llm_response,
                "llm_response_length": len(llm_response),
                "generation_time_ms": generation_time_ms,
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
            
            logger.debug(f"LLM generation logged for {question_id}: {len(llm_response)} chars, {generation_time_ms:.2f}ms")
            logger.debug(f"LLM generation results logged to debug log file: {file_path} for question_id: {question_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log LLM generation results: {ex}")
