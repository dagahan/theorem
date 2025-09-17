from __future__ import annotations
import time
from typing import Dict, Any
import httpx
from loguru import logger
from src.core.utils import EnvTools
from src.domain.models import QuestionResponse
class VLLMAdapter:
    def __init__(self) -> None:
        self.host = EnvTools.required_load_env_var("VLLM_TALKING_HOST")
        self.port = EnvTools.required_load_env_var("VLLM_TALKING_PORT")
        self.model_name = EnvTools.required_load_env_var("VLLM_MODEL_NAME")
        self.base_url = f"http://{self.host}:{self.port}"
        self.client = httpx.AsyncClient(timeout=60.0)


    async def generate_answer(
        self,
        question: str,
        context: str,
        stream: bool = False
    ) -> QuestionResponse:
        start_time = time.time()
        try:
            prompt = self._build_prompt(
                question,
                context
            )
            
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.7,
                "stream": stream
            }
            
            response = await self.client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            
            processing_time = (time.time() - start_time) * 1000
            
            return QuestionResponse(
                answer=answer,
                success=True
            )
            
        except Exception as ex:
            logger.error(f"LLM generation failed: {ex}")
            processing_time = (time.time() - start_time) * 1000
            
            return QuestionResponse(
                answer="",
                success=False,
                error=str(ex)
            )


    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return bool(response.status_code == 200)
        except Exception:
            return False


    def _build_prompt(self, question: str, context: str) -> str:
        return f"""Ты — эксперт по математике ЕГЭ. Используй предоставленный контекст для ответа на вопрос.


Контекст:
{context}

Вопрос: {question}

Ответь подробно и точно, используя информацию из контекста."""



