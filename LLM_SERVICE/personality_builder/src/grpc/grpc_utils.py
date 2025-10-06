from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

import grpc
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
                peer = context.peer() if context and hasattr(context, 'peer') else 'unknown'

                logger.info(f"gRPC request started: {method_name} from {peer}")
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        f"gRPC request failed: {method_name} from {peer} - {exc}"
                    )
                    raise

                logger.info(f"gRPC request completed: {method_name} from {peer}")
                return result

            return wrapper

        return decorator
