from __future__ import annotations

from typing import Dict, Any, List
from loguru import logger

from src.rest.client.base_rest_client import BaseRestClient
from src.core.utils import EnvTools


class VLLMRestClient(BaseRestClient):
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        super().__init__(base_url, timeout)
        self.model_name = EnvTools.required_load_env_var("VLLM_MODEL_NAME")


    async def generate_answer(
        self,
        question: str,
        system_prompt: str,
        context: str = "",
        stream: bool = False
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({"role": "context", "content": context})
            
        messages.append({"role": "user", "content": question})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.2,
            "stop": ["END", "STOP"],
            "stream": stream
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



