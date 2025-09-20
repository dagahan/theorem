from __future__ import annotations

from typing import Any, Dict, TypeVar, cast, Callable
from loguru import logger

from src.core.utils import EnvTools

T = TypeVar('T')


class RestClientRegistry:
    _instance: "RestClientRegistry | None" = None
    _clients: Dict[str, Any]
    

    def __new__(cls) -> "RestClientRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._clients = {}
        return cls._instance


    def register_client(
        self,
        service_name: str,
        client_class: Callable[[str, float], T],
        timeout: float = 30.0,
        **kwargs: Any
    ) -> T:
        if service_name in self._clients:
            return cast("T", self._clients[service_name])
        
        base_url = self._get_service_url(service_name)
        logger.info(f"Creating REST client for {service_name} at {base_url}")
        
        client = client_class(base_url, timeout)
        self._clients[service_name] = client
        
        logger.success(f"REST client created for {service_name}: {base_url}")
        logger.debug(f"REST client registered for {service_name}")

        return client


    def _get_service_url(
        self,
        service_name: str
    ) -> str:
        host = EnvTools.get_service_host(service_name)
        port = EnvTools.get_service_http_port(service_name)

        return f"http://{host}:{port}"


    def get_client(
        self,
        service_name: str
    ) -> Any:
        if service_name not in self._clients:
            raise RuntimeError(f"No client registered for service: {service_name}")

        return self._clients[service_name]


