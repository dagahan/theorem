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


class SearchLogger:
    @staticmethod
    def log_search_pipeline(
        query: str,
        collection_name: str,
        pipeline_steps: Dict[str, Any],
        final_results: List[Dict[str, Any]],
        total_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/search_pipeline"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"search_{timestamp}.json")
            
            search_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "query": query,
                "collection_name": collection_name,
                "total_time_ms": total_time_ms,
                "pipeline_steps": pipeline_steps,
                "final_results_count": len(final_results),
                "final_results": [
                    {
                        "doc_id": result.get("doc_id", ""),
                        "score": result.get("score", 0.0),
                        "pages": result.get("pages", []),
                        "paragraph_id": result.get("paragraph_id", 0),
                        "chunk_id": result.get("chunk_id", 0),
                        "text_preview": result.get("text", "")[:200] + "..." if len(result.get("text", "")) > 200 else result.get("text", "")
                    }
                    for result in final_results
                ]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(search_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log search pipeline: {ex}")


class StepLogger:
    @staticmethod
    def log_step(
        step_name: str,
        step_data: Dict[str, Any],
        execution_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/search_steps"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"{step_name}_{timestamp}.json")
            
            step_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "step_name": step_name,
                "execution_time_ms": execution_time_ms,
                "step_data": step_data
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(step_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log step '{step_name}': {ex}")

    @staticmethod
    def log_search_results(
        search_type: str,
        query: str,
        collection_name: str,
        candidates: List[Dict[str, Any]],
        execution_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/search_results"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"{search_type}_{timestamp}.json")
            
            search_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "search_type": search_type,
                "query": query,
                "collection_name": collection_name,
                "execution_time_ms": execution_time_ms,
                "candidates_count": len(candidates),
                "candidates": [
                    {
                        "doc_id": candidate.get("doc_id", ""),
                        "score": candidate.get("score", 0.0),
                        "pages": candidate.get("pages", []),
                        "paragraph_id": candidate.get("paragraph_id", 0),
                        "chunk_id": candidate.get("chunk_id", 0),
                        "text_preview": candidate.get("text", "")[:200] + "..." if len(candidate.get("text", "")) > 200 else candidate.get("text", "")
                    }
                    for candidate in candidates
                ]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(search_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log {search_type} search results: {ex}")


class ResponseLogger:
    @staticmethod
    def log_response_formatting(
        original_results: List[Dict[str, Any]],
        formatted_text: str,
        formatting_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/response_formatting"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"response_{timestamp}.json")
            
            response_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "original_results_count": len(original_results),
                "formatted_text_length": len(formatted_text),
                "formatting_time_ms": formatting_time_ms,
                "formatted_text_preview": formatted_text[:500] + "..." if len(formatted_text) > 500 else formatted_text,
                "original_results": [
                    {
                        "doc_id": result.get("doc_id", ""),
                        "score": result.get("combined_score", 0.0),
                        "text_preview": result.get("context_text", "")[:100] + "..." if len(result.get("context_text", "")) > 100 else result.get("context_text", "")
                    }
                    for result in original_results
                ]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(response_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log response formatting: {ex}")


class MCPLogger:
    @staticmethod
    def log_tool_call(
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        execution_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/mcp_tool_calls"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"{tool_name}_{timestamp}.json")
            
            tool_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "tool_name": tool_name,
                "execution_time_ms": execution_time_ms,
                "arguments": arguments,
                "result": result
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(tool_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log MCP tool call '{tool_name}': {ex}")

    @staticmethod
    def log_rag_search(
        query: str,
        collection_name: str,
        top_k: int,
        max_context_chars: int,
        digests: List[Dict[str, Any]],
        execution_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/mcp_rag_search"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"rag_search_{timestamp}.json")
            
            rag_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "query": query,
                "collection_name": collection_name,
                "top_k": top_k,
                "max_context_chars": max_context_chars,
                "execution_time_ms": execution_time_ms,
                "digests_count": len(digests),
                "digests": [
                    {
                        "title": digest.get("title", ""),
                        "summary": digest.get("summary", ""),
                        "source_chunk": {
                            "doc_id": digest.get("source_chunk", {}).get("doc_id", ""),
                            "paragraph_id": digest.get("source_chunk", {}).get("paragraph_id", 0),
                            "chunk_id": digest.get("source_chunk", {}).get("chunk_id", 0),
                            "score": digest.get("source_chunk", {}).get("score", 0.0),
                            "pages": digest.get("source_chunk", {}).get("pages", []),
                            "text_preview": digest.get("source_chunk", {}).get("text", "")[:200] + "..." if len(digest.get("source_chunk", {}).get("text", "")) > 200 else digest.get("source_chunk", {}).get("text", "")
                        }
                    }
                    for digest in digests
                ]
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(rag_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log MCP RAG search: {ex}")

    @staticmethod
    def log_grpc_call(
        service_name: str,
        method_name: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        execution_time_ms: float
    ) -> None:
        try:
            debug_dir = "debug/mcp_grpc_calls"
            FileSystemTools.ensure_directory_exists(debug_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(debug_dir, f"{service_name}_{method_name}_{timestamp}.json")
            
            grpc_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "service_name": service_name,
                "method_name": method_name,
                "execution_time_ms": execution_time_ms,
                "request": request_data,
                "response": response_data
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(grpc_entry, file, indent=2, ensure_ascii=False)
            
        except Exception as ex:
            logger.error(f"Failed to log MCP gRPC call '{service_name}.{method_name}': {ex}")