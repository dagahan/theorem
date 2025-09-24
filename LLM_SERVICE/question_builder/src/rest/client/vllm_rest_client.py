from __future__ import annotations

from typing import Dict, Any, List
from loguru import logger

from src.rest.client.base_rest_client import BaseRestClient
from src.core.utils import EnvTools


class VLLMRestClient(BaseRestClient):
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        super().__init__(base_url, timeout)
        self.model_name = EnvTools.required_load_env_var("VLLM_MODEL_NAME")


    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.2
    ) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": ["END", "STOP"]
        }
        
        response = await self._make_request(
            method="POST",
            endpoint="/v1/chat/completions",
            json_data=payload
        )
        
        result = response.json()
        answer = result["choices"][0]["message"]["content"]

        return str(answer.strip())


    async def health_check(self) -> bool:
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health"
            )
            
            return bool(response.status_code == 200)

        except Exception:
            return False



