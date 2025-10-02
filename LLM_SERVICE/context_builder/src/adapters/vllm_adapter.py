from __future__ import annotations

import httpx
from loguru import logger


class VLLMAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout


    async def generate_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            'model': self.model_name,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stop': ['END', 'STOP'],
            'stream': False,
        }
        
        logger.debug(f"VLLM request: model={self.model_name}, max_tokens={max_tokens}, user_prompt_len={len(user_prompt)}")

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            trust_env=False,
        ) as client:
            try:
                response = await client.post('/v1/chat/completions', json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as ex:
                logger.error(f"HTTP {ex.response.status_code}: {ex.response.text}")
                raise

        data = response.json()

        try:
            content = data['choices'][0]['message']['content']

        except (KeyError, IndexError) as ex:
            logger.error('unexpected response from vllm: %s', data)
            raise ValueError('vllm response missing content') from ex

        return str(content).strip()



