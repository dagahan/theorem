import hashlib
import os
import sys
from typing import Any

from loguru import logger


class EnvTools:
    @staticmethod
    def get_env_var(key: str, default: str = "") -> str:
        return os.getenv(key, default)

    @staticmethod
    def set_env_var(key: str, value: str) -> None:
        os.environ[key] = value

    @staticmethod
    def get_service_ip(service_name: str) -> str:
        return EnvTools.get_env_var(f"{service_name.upper()}_HOST", "0.0.0.0")

    @staticmethod
    def get_service_port(service_name: str) -> str:
        return EnvTools.get_env_var(f"{service_name.upper()}_PORT", "50051")