from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from loguru import logger

from src.core.utils import EnvTools


class TimeoutTools:
    _node_timeout: ContextVar[Optional[float]] = ContextVar(
        "node_timeout_sec",
        default=None
    )
    _health_timeout: Optional[float] = None
    _timeout_cache: dict[str, float] = {}


    @staticmethod
    def _load_timeout_from_env(
        variable_name: str,
        default: float
    ) -> float:
        raw_value = EnvTools.load_env_var(variable_name)
        if not raw_value:
            return default

        try:
            parsed = float(raw_value)

        except ValueError:
            logger.warning(
                f"Invalid value '{raw_value}' for {variable_name}, falling back to {default:.2f} sec"
            )
            return default

        if parsed <= 0:
            logger.warning(
                f"Non-positive timeout {parsed:.2f} for {variable_name}, falling back to {default:.2f} sec"
            )
            return default

        return parsed


    @staticmethod
    @contextmanager
    def apply_node_timeout(timeout_sec: Optional[float]) -> Iterator[None]:
        token = TimeoutTools._node_timeout.set(timeout_sec)
        try:
            yield
        finally:
            TimeoutTools._node_timeout.reset(token)


    @staticmethod
    def resolve_node_rpc_timeout(default: Optional[float] = None) -> Optional[float]:
        timeout_sec = TimeoutTools._node_timeout.get()
        if timeout_sec is not None:
            return timeout_sec
        return default


    @classmethod
    def get_health_check_timeout(cls) -> float:
        return cls.get_timeout("HEALTH_CHECK_TIMEOUT_SEC", 5.0)


    @classmethod
    def get_timeout(
        cls,
        variable_name: str,
        default: float,
    ) -> float:
        cached = cls._timeout_cache.get(variable_name)
        if cached is not None:
            return cached

        resolved = cls._load_timeout_from_env(variable_name, default)
        cls._timeout_cache[variable_name] = resolved
        if variable_name == "HEALTH_CHECK_TIMEOUT_SEC":
            cls._health_timeout = resolved
        return resolved

