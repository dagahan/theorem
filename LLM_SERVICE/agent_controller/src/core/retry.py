from __future__ import annotations

import asyncio
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, Sequence, TypeVar

from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.timeouts import TimeoutTools

P = ParamSpec('P')
R = TypeVar('R')


RetryExcType = Sequence[type[BaseException]]


def timeout_and_retry(
    *,
    max_attempts: int,
    timeout_sec: float,
    retry_exceptions: RetryExcType = (asyncio.TimeoutError, ConnectionError),
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    Retry async call with timeout per attempt.
    """
    def decorator(function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                async for attempt in AsyncRetrying(
                    reraise=True,
                    stop=stop_after_attempt(max_attempts),
                    wait=wait_exponential(multiplier=0.2, max=2.0),
                    retry=retry_if_exception_type(tuple(retry_exceptions)),
                    before_sleep=before_sleep_log(logger, 'WARNING'),
                ):
                    with attempt:
                        with TimeoutTools.apply_node_timeout(timeout_sec):
                            return await function(*args, **kwargs)

            except RetryError as exc:
                underlying = exc.last_attempt.exception() if exc.last_attempt else None

                if isinstance(underlying, asyncio.TimeoutError):
                    message = (
                        f"{function.__qualname__} timed out after {timeout_sec:.1f}s "
                        f"(attempts={max_attempts})"
                    )

                    logger.warning(message)
                    raise asyncio.TimeoutError(message) from underlying

                raise

            raise RuntimeError('unreachable')

        return wrapper

    return decorator


