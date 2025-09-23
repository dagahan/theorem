from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Any, Generator, Dict, TypeVar, ParamSpec, Awaitable
import time
from functools import wraps
import grpc
from loguru import logger

from protovalidate import Validator, ValidationError
from src.core.utils import EnvTools

if TYPE_CHECKING:
    import google.protobuf.message
    from grpc import ServicerContext

P = ParamSpec('P')
R = TypeVar('R')


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
    def log_grpc_request(method_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(self: Any, request: Any, context: Any) -> Any:
                start_time = time.time()
                client_info = f"{context.peer()}" if hasattr(context, 'peer') else "unknown"
                
                logger.info(f"gRPC request started: {method_name} from {client_info}")
                
                try:
                    result = await func(self, request, context)
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(f"gRPC request completed: {method_name} from {client_info} in {duration_ms:.2f} ms")
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.error(f"gRPC request failed: {method_name} from {client_info} in {duration_ms:.2f} ms - {str(e)}")
                    raise
            
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
                start_time = time.time()
                channel_info = "unknown"
                if hasattr(args[0], 'channel') and hasattr(args[0].channel, '_channel'):
                    try:
                        channel_info = args[0].channel._channel.target()
                    except:
                        channel_info = str(args[0].channel)
                elif hasattr(args[0], 'channel'):
                    channel_info = str(args[0].channel)
                
                logger.info(f"gRPC client call started: {service_name}.{method_name} to {channel_info}")
                
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    logger.info(f"gRPC client call completed: {service_name}.{method_name} to {channel_info} in {duration_ms:.2f} ms")
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.error(f"gRPC client call failed: {service_name}.{method_name} to {channel_info} in {duration_ms:.2f} ms - {str(e)}")
                    raise
            
            return wrapper

        return decorator


        