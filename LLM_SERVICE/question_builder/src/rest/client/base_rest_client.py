from __future__ import annotations

import httpx
from abc import ABC
from typing import Any, Dict, Optional
from loguru import logger


class BaseRestClient(ABC):
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=timeout, trust_env=False)


    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        endpoint_url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.request(
                method=method,
                url=endpoint_url,
                json=json_data,
                params=params
            )

            response.raise_for_status()

            return response
            
        except httpx.HTTPError as ex:
            logger.error(f"HTTP request failed: {ex}")
            raise

        except Exception as ex:
            logger.error(f"Unexpected error during HTTP request: {ex}")
            raise


    async def close(self) -> None:
        await self.client.aclose()

