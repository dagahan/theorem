from __future__ import annotations
import time
import httpx
from loguru import logger
from src.core.utils import EnvTools


class VLLMAdapter:
    def __init__(self) -> None:
        self.host = EnvTools.required_load_env_var("VLLM_TALKING_HOST")
        self.port = EnvTools.required_load_env_var("VLLM_TALKING_PORT")
        self.model_name = EnvTools.required_load_env_var("VLLM_MODEL_NAME")
        self.base_url = f"http://{self.host}:{self.port}"
        self.client = httpx.AsyncClient(timeout=30.0)


    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        start_time = time.time()
        try:
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = await self.client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            
            processing_time = (time.time() - start_time) * 1000
            logger.debug(f"LLM response generated in {processing_time:.2f} ms")
            
            return str(answer.strip())
            
        except Exception as ex:
            logger.error(f"LLM generation failed: {ex}")
            raise


    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return bool(response.status_code == 200)
        except Exception:
            return False



