from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Any, Generator, Dict
import time
from functools import wraps
import grpc  # type: ignore[import-untyped]
from loguru import logger

from protovalidate import Validator, ValidationError
from src.core.utils import EnvTools

if TYPE_CHECKING:
    import google.protobuf.message  # type: ignore
    from grpc import ServicerContext


class GrpcTools:
    @staticmethod
    def validate_proto(msg: Any, ctx: Any = None) -> None:
        try:
            Validator().validate(msg)
        except ValidationError as e:
            if ctx:
                ctx.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
            else:
                raise ValueError(f"Invalid message: {str(e)}")


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
    def qdrant_normalize(value: Any) -> Any:
        def _norm(d: Dict[str, Any]) -> Dict[str, Any]:
            if "id" in d and isinstance(d["id"], dict):
                d["id"] = d["id"].get("uuid", d["id"].get("num", d["id"]))
            return d

        if isinstance(value, list):
            return [GrpcTools.qdrant_normalize(v) for v in value]
        if isinstance(value, dict):
            value = {k: GrpcTools.qdrant_normalize(v) for k, v in value.items()}
            return _norm(value)
        return value


    @staticmethod
    def log_grpc_request(method_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapper(self: Any, request: Any, context: Any) -> Any:
                start_time = time.time()
                client_info = f"{context.peer()}" if hasattr(context, 'peer') else "unknown"
                
                logger.info(f"gRPC request started: {method_name} from {client_info}")
                
                try:
                    result = func(self, request, context)
                    duration = time.time() - start_time
                    logger.info(f"gRPC request completed: {method_name} from {client_info} in {duration:.3f}s")
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"gRPC request failed: {method_name} from {client_info} in {duration:.3f}s - {str(e)}")
                    raise
            
            return wrapper

        return decorator


