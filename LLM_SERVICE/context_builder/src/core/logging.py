from __future__ import annotations

import inspect
import json
import logging
import os
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from src.pydantic_schemas.context_builder import ContextChunk


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


class ContextBuilderLogger:
    @staticmethod
    def log_chunk_summarization(
        chunk: ContextChunk,
        prompt: str,
        response: dict[str, str] | str | None,
        success: bool,
        processing_time_ms: float,
        error_message: str = "",
        messages: list[dict[str, object]] | None = None,
    ) -> None:
        try:
            debug_dir = "debug/chunk_summarization"
            os.makedirs(debug_dir, exist_ok=True)
            file_path = os.path.join(debug_dir, f"chunk_{chunk.chunk_id}.json")

            chunk_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "paragraph_id": chunk.paragraph_id,
                "score": chunk.score,
                "pages": list(chunk.pages),
                "text_length": len(chunk.text),
                "prompt": prompt,
                "response": response,
                "success": success,
                "error_message": error_message,
                "processing_time_ms": processing_time_ms,
                "status": "success" if success else "failure",
                "messages": messages,
            }

            existing_entries: list[dict[str, object]] = []

            if os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8") as file:
                        data = json.load(file)
                        existing_entries = data.get("chunk_summarization", [])

                except Exception as load_exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to load existing chunk log %s: %s", file_path, load_exc
                    )

            existing_entries.append(chunk_entry)

            log_data = {
                "chunk_id": chunk.chunk_id,
                "chunk_summarization": existing_entries,
            }

            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log chunk summarization results: {ex}")
