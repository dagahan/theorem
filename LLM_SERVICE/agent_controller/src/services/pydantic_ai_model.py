from __future__ import annotations

from typing import TYPE_CHECKING, Any
from loguru import logger

from pydantic_ai.models import ModelResponse, Model
from pydantic_ai.messages import TextPart

if TYPE_CHECKING:
    from src.adapters.vllm_adapter import VLLMAdapter


class PydanticAIBridgeModel(Model):  # type: ignore
    def __init__(
        self,
        *,
        adapter: "VLLMAdapter",
        model_name: str,
        system_prompt: str,
        context: str,
        question: str,
        temperature: float | None,
        max_tokens: int | None,
    ) -> None:
        self.adapter = adapter
        self.model_name_str = model_name
        self.system_prompt = system_prompt
        self.context = context
        self.question = question
        self.temperature = temperature
        self.max_tokens = max_tokens


    @property
    def model_name(self) -> str:
        return self.model_name_str


    @property
    def system(self) -> str:
        return "llm_model_bridge"


    async def request(
        self,
        _messages: list[Any],
        _model_settings: Any,
        _model_request_parameters: Any,
    ) -> ModelResponse:
        logger.debug(f"PydanticAI request: system_prompt_len={len(self.system_prompt)}, question_len={len(self.question)}")
        
        hard_rules = (
            "Return ONLY a valid JSON object that matches the required schema. "
            "No markdown, no code fences, no comments, no bullet points."
        )
        enhanced_system_prompt = f"{self.system_prompt.strip()}\n\n{hard_rules}"

        logger.debug(f"Enhanced system prompt: {enhanced_system_prompt[:200]}...")

        text = await self.adapter.complete(
            system_prompt=enhanced_system_prompt,
            context=self.context,
            question=self.question,
            temperature=0.0,
            max_tokens=self.max_tokens or 1000,
            stream=False,
            response_format={"type": "json_object"},
        )

        logger.debug(f"First response from LLM: {str(text)[:300]}...")

        cleaned_text = self._extract_json_object(str(text or ""))
        logger.debug(f"Extracted JSON: {cleaned_text[:200]}...")
        
        if not cleaned_text.startswith("{"):
            logger.warning("First attempt failed, trying fix prompt")
            fix_prompt = (
                "The previous response was not valid JSON per the required schema. "
                "Output ONLY the corrected JSON object. No prose."
            )
            text2 = await self.adapter.complete(
                system_prompt=f"{enhanced_system_prompt}\n\n{fix_prompt}",
                context="",
                question=f"Here is your previous output:\n{text}",
                temperature=0.0,
                max_tokens=self.max_tokens or 1000,
                stream=False,
                response_format={"type": "json_object"},
            )
            
            logger.debug(f"Second response from LLM: {str(text2)[:300]}...")
            cleaned_text = self._extract_json_object(str(text2 or ""))
            logger.debug(f"Extracted JSON from second attempt: {cleaned_text[:200]}...")
            
            if not cleaned_text.startswith("{"):
                logger.warning("Both attempts failed, creating fallback JSON")
                safe_text = " ".join(str(text2 or "").strip().split())[:1000]
                cleaned_text = f'{{"answer": "{safe_text}", "success": true}}'

        logger.debug(f"Final JSON result: {cleaned_text[:200]}...")
        return ModelResponse(
            parts=[TextPart(content=cleaned_text)],
            model_name=self.model_name_str
        )

    @staticmethod
    def _extract_json_object(text: str) -> str:
        import json
        import re
        
        logger.debug(f"Extracting JSON from text ({len(text)} chars): {text[:200]}...")
        
        t = text.strip()
        
        if t.startswith("```"):
            logger.debug("Removing code block markers")
            t = t.strip("`")
            t = re.sub(r"^json\s*", "", t, flags=re.IGNORECASE)
        
        try:
            logger.debug("Trying to parse entire text as JSON")
            json.loads(t)
            logger.debug("Entire text is valid JSON")
            return t
        except Exception as e:
            logger.debug(f"Entire text is not valid JSON: {e}")
        
        code_block_pattern = r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```'
        m = re.search(code_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            try:
                json.loads(candidate)
                logger.debug(f"Found JSON in code block: {candidate[:100]}...")
                return candidate
            except Exception as e:
                logger.debug(f"Code block JSON invalid: {e}")
        
        def _largest_balanced_fragment(s: str) -> str | None:
            stack: list[str] = []
            start = None
            best = None
            for i, ch in enumerate(s):
                if ch in "{[":
                    if not stack:
                        start = i
                    stack.append(ch)
                elif ch in "}]":
                    if not stack:
                        continue
                    open_ch = stack.pop()
                    if (open_ch, ch) not in (("{","}"), ("[","]")):
                        stack = []
                        start = None
                        continue
                    if not stack and start is not None:
                        frag = s[start:i+1]
                        if best is None or len(frag) > len(best):
                            best = frag
            return best

        candidate = _largest_balanced_fragment(t)
        if candidate:
            try:
                json.loads(candidate)
                logger.debug(f"Found largest balanced JSON: {candidate[:100]}...")
                return candidate
            except Exception as e:
                logger.debug(f"Largest balanced JSON invalid: {e}")
        
        logger.debug("No valid JSON found, returning original text")
        return text



