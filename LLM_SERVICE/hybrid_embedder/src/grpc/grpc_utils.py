from __future__ import annotations

from typing import Any, Awaitable, Callable, ParamSpec, TypeVar
import time
from functools import wraps

import grpc  # type: ignore[import-untyped]
from loguru import logger

from protovalidate import ValidationError, Validator


P = ParamSpec("P")
R = TypeVar("R")


class GrpcTools:
    @staticmethod
    def validate_proto(msg: Any, ctx: Any = None) -> None:
        try:
            Validator().validate(msg)
        except ValidationError as e:
            details = []
            for v in getattr(e, "violations", []) or []:
                details.append(f"path={getattr(v,'field_path', '')} msg={getattr(v,'message','')}")
            text_details_ex = "; ".join(details) or str(e)
            if ctx:
                ctx.abort(grpc.StatusCode.INVALID_ARGUMENT, text_details_ex)
            else:
                logger.error(f"Validation failed: {text_details_ex}")
                raise ValueError(f"Invalid message: {text_details_ex}")

    @staticmethod
    def log_grpc_request(
        method_name: str,
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                start_time = time.time()
                context: Any | None = kwargs.get("context")
                if context is None and len(args) >= 3:
                    context = args[2]
                client_info = f"{context.peer()}" if context and hasattr(context, "peer") else "unknown"

                logger.info(f"gRPC request started: {method_name} from {client_info}")

                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(
                        f"gRPC request completed: {method_name} from {client_info} in {duration_ms:.2f} ms"
                    )
                    return result

                except Exception as e:  # noqa: BLE001
                    duration_ms = (time.time() - start_time) * 1000
                    logger.error(
                        f"gRPC request failed: {method_name} from {client_info} in {duration_ms:.2f} ms - {str(e)}"
                    )
                    raise

            return wrapper

        return decorator
