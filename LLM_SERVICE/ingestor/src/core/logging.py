import inspect
import json
import logging
import os
import re
import sys
import unicodedata
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


class ChunkingLogger:
    @staticmethod
    def log_chunking_results(
        doc_id: str,
        extracted_text: str,
        chunks: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        paragraph_count: int
    ) -> None:
        try:
            log_chunking_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "doc_id": doc_id,
                "metadata": metadata,
                "extracted_text_length": len(extracted_text),
                "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
                "chunks_count": len(chunks),
                "chunks": [
                    {
                        "chunk_id": chunk.get("chunk_id", chunk.get("id", "")),
                        "paragraph_id": chunk.get("paragraph_id", ""),
                        "text_length": len(chunk["text"]),
                        "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                        "pages": chunk.get("pages", [])
                    }
                    for chunk in chunks
                ]
            }
            
            debug_dir = "debug/chunking"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{doc_id}.json")
            
            with open(file_path, "a", encoding="utf-8") as file:
                file.write(json.dumps(log_chunking_entry, indent=2, ensure_ascii=False))
                file.write("\n\n")
            
            logger.debug(f"Document {doc_id} chunked: {len(chunks)} chunks, {paragraph_count} paragraphs")
            logger.debug(f"Processing results logged to debug log file: {file_path} for doc_id: {doc_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log processing results: {ex}")


class TextNormalizeLogger:
    @staticmethod
    def log_normalization_results(
        doc_id: str,
        normalized_text: str,
        metadata: Dict[str, Any],
        original_length: int,
        normalized_length: int
    ) -> None:
        try:
            debug_dir = "debug/text_normalization"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{doc_id}.json")
            
            normalization_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "original_text_length": original_length,
                "normalized_text_length": normalized_length,
                "compression_ratio": round(normalized_length / original_length, 3) if original_length > 0 else 0,
                "normalized_text": normalized_text,
                "length_changed": original_length != normalized_length
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "doc_id": doc_id,
                "metadata": metadata,
                "normalizations": [normalization_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
            logger.debug(f"Text normalization logged for {doc_id}: {original_length} -> {normalized_length} chars")
            logger.debug(f"Normalization results logged to debug log file: {file_path} for doc_id: {doc_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log normalization results: {ex}")


class FileParserLogger:
    @staticmethod
    def log_parsing_results(
        doc_id: str,
        content_type: str,
        extracted_text: str,
        metadata: Dict[str, Any],
        parsing_method: str,
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/file_parsing"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{doc_id}.json")
            
            parsing_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "doc_id": doc_id,
                "content_type": content_type,
                "parsing_method": parsing_method,
                "success": success,
                "extracted_text_length": len(extracted_text),
                "extracted_text": extracted_text,
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "doc_id": doc_id,
                "metadata": metadata,
                "parsing_results": [parsing_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
            logger.debug(f"File parsing logged for {doc_id}: {len(extracted_text)} chars using {parsing_method}")
            logger.debug(f"Parsing results logged to debug log file: {file_path} for doc_id: {doc_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log parsing results: {ex}")


class BlockingLogger:
    @staticmethod
    def log_blocking_results(
        doc_id: str,
        content_type: str,
        blocks: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        success: bool,
        error_message: str = ""
    ) -> None:
        try:
            debug_dir = "debug/blocking"
            FileSystemTools.ensure_directory_exists(debug_dir)
            file_path = os.path.join(debug_dir, f"{doc_id}.json")
            
            blocking_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "doc_id": doc_id,
                "content_type": content_type,
                "success": success,
                "blocks_count": len(blocks),
                "blocks": [
                    {
                        "page": block.get("page", 0),
                        "kind": block.get("kind", ""),
                        "text_length": len(block.get("text", "")),
                        "text_preview": block.get("text", "")[:200] + "..." if len(block.get("text", "")) > 200 else block.get("text", ""),
                        "bbox": block.get("bbox", (0, 0, 0, 0)),
                        "meta": block.get("meta", {})
                    }
                    for block in blocks
                ],
                "error_message": error_message if not success else None
            }
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            log_data = {
                "doc_id": doc_id,
                "metadata": metadata,
                "blocking_results": [blocking_entry]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(log_data, file, indent=2, ensure_ascii=False)
            
            logger.debug(f"Blocking logged for {doc_id}: {len(blocks)} blocks")
            logger.debug(f"Blocking results logged to debug log file: {file_path} for doc_id: {doc_id}")
            
        except Exception as ex:
            logger.error(f"Failed to log blocking results: {ex}")


