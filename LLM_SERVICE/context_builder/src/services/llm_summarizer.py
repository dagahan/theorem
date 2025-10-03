from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterable, Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, ModelResponse

from src.core.logging import ContextBuilderLogger
from src.pydantic_schemas.context_builder import ContextChunk, DigestItem, SummarizerConfig, SummarizerDigestPayload

if TYPE_CHECKING:
    from pydantic_ai.run import AgentRun

    from src.services.personality_client import PersonalityClient


def _apply_token_budget(config: SummarizerConfig, token_budget: int) -> SummarizerConfig:
    bounded = max(config.min_tokens, min(config.max_tokens_cap, token_budget))
    return SummarizerConfig(
        model_name=config.model_name,
        temperature=config.temperature,
        max_tokens=bounded,
        min_tokens=config.min_tokens,
        max_tokens_cap=config.max_tokens_cap,
        chars_per_token=config.chars_per_token,
        max_concurrency=config.max_concurrency
    )


class _PersonalityModel(Model):  # type: ignore[misc]
    def __init__(self, *, config: SummarizerConfig, client: PersonalityClient) -> None:
        self._config = config
        self._client = client


    @property
    def model_name(self) -> str:
        return str(self._config.model_name)


    @property
    def system(self) -> str:
        return "summarizer"


    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        instructions = self._extract_instructions(messages)

        schema_hint = self._schema_hint(model_request_parameters)

        system_prompt = self._merge_non_empty(instructions, schema_hint) or ''

        user_prompt = self._extract_user_prompt(messages)

        response_text = await self._client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )

        return ModelResponse(
            parts=[TextPart(content=response_text)],
            model_name=self._config.model_name
        )


    @staticmethod
    def _extract_instructions(messages: Iterable[ModelMessage]) -> str | None:
        for message in reversed(list(messages)):
            if isinstance(message, ModelRequest) and message.instructions:
                return message.instructions  # type: ignore

        return None


    @staticmethod
    def _schema_hint(parameters: ModelRequestParameters) -> str | None:
        output_obj = parameters.output_object

        if output_obj is None:
            return None

        schema_json = output_obj.json_schema.model_dump_json(indent=2)

        return (
            'YOU MUST respond with JSON that strictly matches the following schema. '
            'Return only valid JSON without commentary.\n'
            f'{schema_json}'
        )


    @staticmethod
    def _extract_user_prompt(messages: Iterable[ModelMessage]) -> str:
        parts: list[str] = []

        for message in messages:
            if not isinstance(message, ModelRequest):
                continue

            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    if isinstance(part.content, str):
                        parts.append(part.content)

                    elif isinstance(part.content, Iterable):
                        parts.extend(str(item) for item in part.content)

        return '\n'.join(segment for segment in parts if segment.strip())


    @staticmethod
    def _merge_non_empty(*parts: str | None) -> str | None:
        values = [part.strip() for part in parts if part and part.strip()]
        return '\n\n'.join(values) if values else None


class LLMSummarizer:
    def __init__(
        self,
        *,
        config: SummarizerConfig,
        personality_client: PersonalityClient,
    ) -> None:
        self._config = config
        self._client = personality_client


    async def summarize(
        self,
        *,
        persona_prompt: str,
        chunks: Sequence[ContextChunk],
        max_chunk_chars: int,
    ) -> list[DigestItem]:
        start_time = time.time()
        chunk_count = len(chunks)
        if chunk_count == 0:
            return []

        logger.info(f"LLM summarization: processing {chunk_count} chunks in parallel")

        token_budget = self._calculate_token_budget(chunk_count, max_chunk_chars)
        runtime_config = _apply_token_budget(self._config, token_budget)
        semaphore = asyncio.Semaphore(max(1, runtime_config.max_concurrency))

        tasks = [
            self._summarize_chunk(
                position=index,
                persona_prompt=persona_prompt,
                chunk=chunk,
                max_chunk_chars=max_chunk_chars,
                semaphore=semaphore,
                runtime_config=runtime_config,
            )
            for index, chunk in enumerate(chunks, start=1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        ordered: list[tuple[int, DigestItem]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Summarization task failed: {result}")
                continue

            if isinstance(result, tuple) and len(result) == 2:
                position, digest = result
                if digest is not None:
                    ordered.append((position, digest))

        ordered.sort(key=lambda pair: pair[0])
        digests = [digest for _, digest in ordered]

        total_time_ms = (time.time() - start_time) * 1000.0
        logger.info(
            f"LLM summarization completed: {len(digests)} digests prepared in "
            f"{total_time_ms:.2f}ms (token budget per chunk ≈ {runtime_config.max_tokens})"
        )

        return digests


    async def _summarize_chunk(
        self,
        position: int,
        *,
        persona_prompt: str,
        chunk: ContextChunk,
        max_chunk_chars: int,
        semaphore: asyncio.Semaphore,
        runtime_config: SummarizerConfig,
    ) -> tuple[int, DigestItem | None]:
        start_time = time.time()

        async with semaphore:
            model = _PersonalityModel(config=runtime_config, client=self._client)
            agent = Agent(
                model=model,
                output_type=SummarizerDigestPayload,
                instructions=persona_prompt,
                retries=2,
            )

            chunk_prompt = self._build_single_chunk_prompt(chunk, max_chunk_chars)
            logger.debug(
                "Summarizing chunk %s with prompt length=%s chars (tokens≈%s)",
                chunk.chunk_id,
                len(chunk_prompt),
                runtime_config.max_tokens,
            )

            digest: DigestItem | None = None
            error_message = ""
            response_payload: dict[str, str] | str | None = None
            raw_messages: list[dict[str, object]] | None = None
            agent_run: AgentRun[Any, SummarizerDigestPayload] | None = None

            try:
                async with agent.iter(user_prompt=chunk_prompt) as run:
                    agent_run = run
                    async for _ in run:
                        pass

                if agent_run is None or agent_run.result is None:
                    raise RuntimeError('Summarizer produced no result')

                payload = agent_run.result.output

                summary_text = self._normalize_summary(payload.summary)
                label = f'digest_{position}'

                digest = DigestItem(
                    title=label,
                    summary=f'{label}: {summary_text}',
                    source_chunk=chunk,
                )

                response_payload = {
                    'title': (payload.title or '').strip(),
                    'summary': summary_text,
                }

                raw_messages = self._serialize_messages(agent_run.result.all_messages())

                logger.debug(
                    "Chunk %s summarized (%s)",
                    chunk.chunk_id,
                    label,
                )

            except Exception as ex:  # noqa: BLE001
                error_message = str(ex)
                logger.error(f"Failed to summarize chunk {chunk.chunk_id}: {ex}")

                if agent_run is not None:
                    raw_messages = self._serialize_messages(agent_run.ctx.state.message_history)

            processing_time_ms = (time.time() - start_time) * 1000.0

            ContextBuilderLogger.log_chunk_summarization(
                chunk=chunk,
                prompt=chunk_prompt,
                response=response_payload,
                success=digest is not None,
                processing_time_ms=processing_time_ms,
                error_message=error_message,
                messages=raw_messages,
            )

        return position, digest


    def _build_single_chunk_prompt(
        self,
        chunk: ContextChunk,
        max_chars: int,
    ) -> str:
        header = (
            f"chunk_id={chunk.chunk_id}; doc_id={chunk.doc_id}; "
            f"paragraph_id={chunk.paragraph_id}; score={chunk.score:.4f}; "
            f"pages={','.join(str(page) for page in chunk.pages) or '—'}"
        )

        text = self._clip_text(chunk.text, max_chars)
        
        return f"{header}\n\n{text}"


    @staticmethod
    def _clip_text(
        text: str,
        limit: int
    ) -> str:
        if limit <= 0 or len(text) <= limit:
            return text

        truncated = text[: max(0, limit - 3)].rstrip()
        return f'{truncated}...'


    def _calculate_token_budget(
        self,
        chunk_count: int,
        max_context_chars: int,
    ) -> int:
        if chunk_count <= 0:
            return int(self._config.max_tokens)

        approx_tokens = max_context_chars // max(1, chunk_count)
        approx_tokens = approx_tokens // max(1, self._config.chars_per_token)

        if approx_tokens <= 0:
            approx_tokens = self._config.min_tokens

        return int(max(self._config.min_tokens, min(self._config.max_tokens_cap, approx_tokens)))


    @staticmethod
    def _normalize_summary(summary: str) -> str:
        cleaned = ' '.join(summary.strip().split())
        return cleaned

    @staticmethod
    def _serialize_messages(
        messages: Sequence[ModelMessage],
    ) -> list[dict[str, object]] | None:
        try:
            packed = ModelMessagesTypeAdapter.dump_json(list(messages))
        except Exception:
            return None

        try:
            if isinstance(packed, bytes | bytearray):
                return cast(list[dict[str, object]], json.loads(packed.decode('utf-8')))
            return cast(list[dict[str, object]], json.loads(packed))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None


    @staticmethod
    def _linearize_digests(digests: Sequence[DigestItem]) -> str:
        parts = [digest.summary.strip() for digest in digests if digest.summary.strip()]
        return ' '.join(parts)
