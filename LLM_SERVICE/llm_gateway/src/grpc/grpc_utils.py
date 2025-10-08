from __future__ import annotations

import contextlib
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, ParamSpec, TypeVar

import grpc  # type: ignore[import-untyped]
from loguru import logger
from protovalidate import ValidationError, Validator



if TYPE_CHECKING:
    import google.protobuf.message  # type: ignore[import-untyped]
    from grpc import ServicerContext


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
    def proto_to_dict(msg: Any) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for field in msg.DESCRIPTOR.fields:
            value = getattr(msg, field.name)
            if field.type == field.TYPE_MESSAGE:
                if field.label == field.LABEL_REPEATED:
                    result[field.name] = [GrpcTools.proto_to_dict(item) for item in value]
                else:
                    result[field.name] = GrpcTools.proto_to_dict(value) if value else None
            elif field.type == field.TYPE_ENUM:
                result[field.name] = value.name if value else None
            else:
                result[field.name] = value
        return result


    @staticmethod
    def log_grpc_request(
        method_name: str
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                context: Any | None = kwargs.get('context')
                if context is None and len(args) >= 3:
                    context = args[2]

                peer = context.peer() if context and hasattr(context, 'peer') else 'unknown'
                start_time = time.time()
                logger.info(f"gRPC request started: {method_name} from {peer}")

                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    duration_ms = (time.time() - start_time) * 1000
                    logger.error(
                        f"gRPC request failed: {method_name} from {peer} in {duration_ms:.2f} ms - {exc}"
                    )
                    raise

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"gRPC request completed: {method_name} from {peer} in {duration_ms:.2f} ms"
                )
                return result

            return wrapper

        return decorator


    @staticmethod
    def log_grpc_client_call(
        service_name: str,
        method_name: str
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
            @wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                client = args[0] if args else None
                client_service = getattr(client, 'service_name', service_name) if client else service_name
                target = getattr(client, 'target', None) if client else None

                channel = getattr(client, 'channel', None) if client else None
                if not target and channel is not None:
                    target = getattr(channel, '_target', None)
                    if not target and hasattr(channel, '_channel'):
                        with contextlib.suppress(Exception):  # noqa: BLE001
                            target = channel._channel.target()
                address = target or 'unknown'

                start_time = time.time()
                logger.info(
                    f"gRPC client call started: {client_service}.{method_name} -> {address}"
                )

                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    duration_ms = (time.time() - start_time) * 1000
                    logger.error(
                        f"gRPC client call failed: {client_service}.{method_name} -> {address} "
                        f"in {duration_ms:.2f} ms - {exc}"
                    )
                    raise

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"gRPC client call completed: {client_service}.{method_name} -> {address} "
                    f"in {duration_ms:.2f} ms"
                )
                return result

            return wrapper

        return decorator


