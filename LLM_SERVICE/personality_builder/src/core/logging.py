import inspect
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


class InterceptHandler(logging.Handler):  # type: ignore[misc,name-defined]
    def emit(self, record: Any) -> None:
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


class PersonalityBuilderLogger:
    @staticmethod
    def log_personality_build_results(
        persona_names: List[str],
        agent_name: str,
        personalities: List[Dict[str, Any]],
        success: bool,
        error_message: str = "",
        policy_header: Optional[str] = None
    ) -> None:
        try:
            debug_dir = "debug/personality_building"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
            file_path = os.path.join(debug_dir, f"personality_build_{timestamp}.json")
            
            build_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "persona_names": persona_names,
                "agent_name": agent_name,
                "success": success,
                "personalities_count": len(personalities),
                "personalities": [
                    {
                        "name": personality.get("name", ""),
                        "system_prompt_length": len(personality.get("system_prompt", "")),
                        "system_prompt_preview": personality.get("system_prompt", "")[:500] + "..." if len(personality.get("system_prompt", "")) > 500 else personality.get("system_prompt", ""),
                        "has_response_schema": personality.get("response_schema") is not None,
                        "response_schema": personality.get("response_schema")
                    }
                    for personality in personalities
                ],
                "policy_header_length": len(policy_header) if policy_header else 0,
                "policy_header_preview": policy_header[:200] + "..." if policy_header and len(policy_header) > 200 else policy_header,
                "error_message": error_message if not success else None
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(build_entry, file, indent=2, ensure_ascii=False)
            
            logger.debug(f"Personality build results logged to {file_path}")
            
        except Exception as ex:
            logger.error(f"Failed to log personality build results: {ex}")


class SchemaStoreLogger:
    @staticmethod
    def log_schema_load_results(
        persona: str,
        schema_data: Optional[Dict[str, Any]],
        success: bool,
        error_message: str = "",
        schema_file_path: Optional[str] = None
    ) -> None:
        try:
            debug_dir = "debug/schema_loading"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
            file_name = f"schema_load_{persona}_{timestamp}.json"
            log_file_path = os.path.join(debug_dir, file_name)
            
            schema_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "persona": persona,
                "success": success,
                "schema_file_path": schema_file_path,
                "schema_data": schema_data,
                "schema_type": schema_data.get("type") if schema_data else None,
                "schema_properties_count": len(schema_data.get("properties", {})) if schema_data else 0,
                "schema_required_fields": schema_data.get("required", []) if schema_data else [],
                "error_message": error_message if not success else None
            }
            
            with open(log_file_path, "w", encoding="utf-8") as file:
                json.dump(schema_entry, file, indent=2, ensure_ascii=False)
            
            logger.debug(f"Schema load results for {persona} logged to {log_file_path}")
            
        except Exception as ex:
            logger.error(f"Failed to log schema load results: {ex}")


class TemplateRenderLogger:
    @staticmethod
    def log_template_render_results(
        persona: str,
        template_name: str,
        rendered_prompt: str,
        success: bool,
        error_message: str = "",
        template_vars: Optional[Dict[str, Any]] = None
    ) -> None:
        try:
            debug_dir = "debug/template_rendering"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
            file_name = f"template_render_{persona}_{timestamp}.json"
            file_path = os.path.join(debug_dir, file_name)
            
            render_entry = {
                "timestamp": int(datetime.now().timestamp()),
                "persona": persona,
                "template_name": template_name,
                "success": success,
                "rendered_prompt_length": len(rendered_prompt),
                "rendered_prompt_preview": rendered_prompt[:500] + "..." if len(rendered_prompt) > 500 else rendered_prompt,
                "template_vars": template_vars,
                "error_message": error_message if not success else None
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(render_entry, file, indent=2, ensure_ascii=False)
            
            logger.debug(f"Template render results for {persona} logged to {file_path}")
            
        except Exception as ex:
            logger.error(f"Failed to log template render results: {ex}")



