from typing import Any, Dict, TypeVar, cast, Callable
import grpc.aio
from loguru import logger

from src.core.utils import EnvTools

T = TypeVar('T')


class GrpcClientRegistry:
    _instance: "GrpcClientRegistry | None" = None
    _clients: Dict[str, Any]
    _channels: Dict[str, grpc.aio.Channel]
    

    def __new__(cls) -> "GrpcClientRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._clients = {}
            cls._instance._channels = {}
        return cls._instance


    def _get_channel(
        self,
        service_name: str
    ) -> tuple[grpc.aio.Channel, str]:
        if service_name in self._channels:
            channel = self._channels[service_name]
            target = getattr(channel, '_target', None)
            if isinstance(target, str):
                return channel, target
        
        host = EnvTools.get_service_host(service_name)
        port = EnvTools.get_service_grpc_port(service_name)
        address = f"{host}:{port}"
        logger.info(f"Creating gRPC channel for {service_name} at {address}")
        
        options = [
            ('grpc.keepalive_time_ms', 240000),
            ('grpc.keepalive_timeout_ms', 10000),
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.max_receive_message_length', 4 * 1024 * 1024),
            ('grpc.max_send_message_length', 4 * 1024 * 1024),
            ('grpc.enable_http_proxy', 0),
        ]

        channel = grpc.aio.insecure_channel(address, options=options)
        setattr(channel, '_target', address)
        self._channels[service_name] = channel
        logger.success(f"gRPC channel created for {service_name}: {address}")

        return channel, address


    def register_client(
        self,
        service_name: str,
        client_class: Callable[..., T],
        **kwargs: Any
    ) -> T:
        if service_name in self._clients:
            return cast("T", self._clients[service_name])
        
        channel, target = self._get_channel(service_name)
        client = client_class(channel, service_name, target=target, **kwargs)

        self._clients[service_name] = client

        logger.debug(f"gRPC client registered for {service_name} -> {target}")

        return client


    def get_client(
        self,
        service_name: str
    ) -> Any:
        if service_name not in self._clients:
            raise RuntimeError(f"No client registered for service: {service_name}")

        return self._clients[service_name]



