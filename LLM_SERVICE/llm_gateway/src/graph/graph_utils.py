from __future__ import annotations
import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type

P = ParamSpec("P")
R = TypeVar("R")


def timeout_and_retry(
    max_attempts: int,
    timeout_sec: float,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=0.2, max=2.0),
                retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
            ):
                with attempt:
                    async with asyncio.timeout(timeout_sec):
                        return await fn(*args, **kwargs)

            raise RuntimeError("unreachable")

        return wrapper
        
    return decorator



