"""Google Gemini provider via official google-genai SDK."""

import asyncio
import logging
import time
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from csc.config import settings
from csc.llm.exceptions import LlmError
from csc.llm.providers.base import BatchItem, ProviderResponse

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Official Google Gemini provider encapsulating google-genai client."""

    def __init__(
        self,
        api_key: str | None = None,
        free_api_key: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.free_api_key = free_api_key or settings.gemini_free_api_key
        self._paid_client: genai.Client | None = None
        self._free_client: genai.Client | None = None

    def _get_client(self, tier: str = "paid") -> genai.Client:
        is_free = tier.lower() == "free"
        if is_free:
            if self._free_client is not None:
                return self._free_client
            key = self.free_api_key or self.api_key
            if not key:
                raise LlmError(
                    "No Gemini API key available for tier 'free'. "
                    "Please configure GEMINI_FREE_API_KEY or GEMINI_API_KEY in environment or .env."
                )
            self._free_client = genai.Client(api_key=key)
            return self._free_client
        else:
            if self._paid_client is not None:
                return self._paid_client
            key = self.api_key
            if not key:
                raise LlmError(
                    "No Gemini API key available for tier 'paid'. "
                    "Please configure GEMINI_API_KEY in environment or .env."
                )
            self._paid_client = genai.Client(api_key=key)
            return self._paid_client

    def _build_generate_config(
        self,
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
    ) -> types.GenerateContentConfig:
        p = params or {}
        config_kwargs: dict[str, Any] = {
            "temperature": float(p.get("temperature", 0.0)),
            "max_output_tokens": int(p.get("max_output_tokens", 4096)),
        }

        if schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = schema

        thinking_val = p.get("thinking")
        if thinking_val:
            if isinstance(thinking_val, str) and thinking_val.lower() in ("low", "medium", "high"):
                level_enum = getattr(
                    types.ThinkingLevel, thinking_val.upper(), types.ThinkingLevel.LOW
                )
                config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=level_enum)
            elif isinstance(thinking_val, int):
                config_kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_budget=thinking_val
                )

        return types.GenerateContentConfig(**config_kwargs)

    async def generate(
        self,
        model: str,
        prompt: str,
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        tier: str = "paid",
    ) -> ProviderResponse:
        client = self._get_client(tier=tier)
        config = self._build_generate_config(schema=schema, params=params)

        start_t = time.perf_counter()
        max_retries = 3
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                latency = int((time.perf_counter() - start_t) * 1000)

                raw_text = response.text or ""
                usage = response.usage_metadata

                in_tok = usage.prompt_token_count if usage and usage.prompt_token_count else 0
                cached_tok = (
                    usage.cached_content_token_count
                    if usage and usage.cached_content_token_count
                    else 0
                )
                out_tok = (
                    usage.candidates_token_count if usage and usage.candidates_token_count else 0
                )
                think_tok = (
                    usage.thoughts_token_count if usage and usage.thoughts_token_count else 0
                )

                return ProviderResponse(
                    text=raw_text,
                    raw_output=raw_text,
                    input_tokens=in_tok,
                    cached_tokens=cached_tok,
                    output_tokens=out_tok,
                    thinking_tokens=think_tok,
                    latency_ms=latency,
                )
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        "Gemini generate_content failed after %d retries: %s", max_retries, e
                    )
                    raise LlmError(f"Gemini API generation failed: {e}") from e
                logger.warning(
                    "Gemini API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_retries,
                    e,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff *= 2.0

        raise LlmError("Gemini generate_content retries exhausted.")

    async def submit_batch(
        self,
        model: str,
        items: list[BatchItem],
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        tier: str = "paid",
    ) -> str:
        client = self._get_client(tier=tier)
        gen_config = self._build_generate_config(schema=schema, params=params)

        inlined_requests: list[types.InlinedRequest] = []
        for item in items:
            req = types.InlinedRequest(
                contents=item.prompt,
                config=gen_config,
                metadata={"custom_id": item.custom_id},
            )
            inlined_requests.append(req)

        batch_job = await client.aio.batches.create(
            model=model,
            src=inlined_requests,
        )
        return str(batch_job.name)

    async def collect_batch(self, job_id: str) -> list[ProviderResponse]:
        client = self._get_client(tier="paid")
        batch_job = await client.aio.batches.get(name=job_id)

        # Check for batch failure
        if batch_job.state == types.JobState.JOB_STATE_FAILED:
            raise LlmError(f"Gemini batch job '{job_id}' failed: {batch_job.error}")

        # Batch job processing or completion check
        results: list[ProviderResponse] = []
        # If dest or inlined responses exist
        if batch_job.dest and hasattr(batch_job.dest, "inlined_responses"):
            for resp in batch_job.dest.inlined_responses or []:
                raw_text = str(resp.response.text) if resp.response and resp.response.text else ""
                usage = resp.response.usage_metadata if resp.response else None
                in_tok = usage.prompt_token_count if usage and usage.prompt_token_count else 0
                cached_tok = (
                    usage.cached_content_token_count
                    if usage and usage.cached_content_token_count
                    else 0
                )
                out_tok = (
                    usage.candidates_token_count if usage and usage.candidates_token_count else 0
                )
                think_tok = (
                    usage.thoughts_token_count if usage and usage.thoughts_token_count else 0
                )
                results.append(
                    ProviderResponse(
                        text=raw_text,
                        raw_output=raw_text,
                        input_tokens=in_tok,
                        cached_tokens=cached_tok,
                        output_tokens=out_tok,
                        thinking_tokens=think_tok,
                    )
                )
        return results

    async def count_tokens(self, model: str, prompt: str) -> int:
        client = self._get_client(tier="paid")
        try:
            res = await client.aio.models.count_tokens(model=model, contents=prompt)
            return int(res.total_tokens or 0)
        except Exception:
            # Fallback estimation if count_tokens is unavailable
            words = len(prompt.split())
            return max(1, int(words * 1.3))
