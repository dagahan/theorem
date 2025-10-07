from __future__ import annotations

import time
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

import grpc  # type: ignore[import-untyped]
from loguru import logger
from protovalidate import ValidationError, Validator


P = ParamSpec('P')
R = TypeVar('R')


class GrpcTools:
    @staticmethod
    def validate_proto(msg: Any, ctx: Any | None = None) -> None:
        try:
            Validator().validate(msg)
        except ValidationError as exc:  # noqa: BLE001
            details = []
            for violation in getattr(exc, 'violations', []) or []:
                details.append(
                    f"path={getattr(violation, 'field_path', '')} msg={getattr(violation, 'message', '')}"
                )
            formatted = '; '.join(details) or str(exc)
            if ctx:
                ctx.abort(grpc.StatusCode.INVALID_ARGUMENT, formatted)
            logger.error(f"Validation failed: {formatted}")
            raise ValueError(f"Invalid message: {formatted}") from exc

    @staticmethod
    def log_grpc_request(
        method_name: str,
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                context: Any | None = kwargs.get('context')
                if context is None and len(args) >= 3:
                    context = args[2]
                
                peer = 'unknown'
                if context and hasattr(context, 'peer'):
                    try:
                        peer = context.peer()
                    except Exception:
                        peer = 'unknown'

                logger.info(f"gRPC request started: {method_name} from {peer}")
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    logger.info(f"gRPC request completed: {method_name} from {peer} in {duration_ms:.2f} ms")
                    return result
                except Exception as exc:  # noqa: BLE001
                    end_time = time.time()
                    duration_ms = (end_time - start_time) * 1000
                    logger.error(
                        f"gRPC request failed: {method_name} from {peer} in {duration_ms:.2f} ms - {exc}"
                    )
                    raise

            return wrapper

        return decorator
