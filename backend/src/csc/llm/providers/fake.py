"""Deterministic fake LLM provider for tests and local development."""

import json
import uuid
from typing import Any

from pydantic import BaseModel

from csc.llm.providers.base import BatchItem, ProviderResponse


class FakeProvider:
    """Configurable fake provider returning deterministic or queued responses."""

    def __init__(
        self,
        default_response: str | dict[str, Any] | BaseModel = "Fake LLM output",
        input_tokens: int = 100,
        output_tokens: int = 50,
        cached_tokens: int = 0,
        thinking_tokens: int = 0,
    ) -> None:
        self.default_response = self._serialize_output(default_response)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached_tokens = cached_tokens
        self.thinking_tokens = thinking_tokens

        # Queue of pre-scripted responses for sequential calls (e.g. invalid then valid)
        self.response_queue: list[str] = []
        self.call_history: list[dict[str, Any]] = []
        self.batch_jobs: dict[str, list[ProviderResponse]] = {}

    def _serialize_output(self, val: str | dict[str, Any] | BaseModel) -> str:
        if isinstance(val, BaseModel):
            return val.model_dump_json()
        if isinstance(val, dict):
            return json.dumps(val)
        return str(val)

    def enqueue_response(self, val: str | dict[str, Any] | BaseModel) -> None:
        """Enqueue a scripted response to be returned by next call."""
        self.response_queue.append(self._serialize_output(val))

    async def generate(
        self,
        model: str,
        prompt: str,
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        tier: str = "paid",
    ) -> ProviderResponse:
        self.call_history.append(
            {
                "model": model,
                "prompt": prompt,
                "schema": schema,
                "params": params or {},
                "tier": tier,
            }
        )

        if self.response_queue:
            raw_text = self.response_queue.pop(0)
        else:
            raw_text = self.default_response

        return ProviderResponse(
            text=raw_text,
            raw_output=raw_text,
            input_tokens=self.input_tokens,
            cached_tokens=self.cached_tokens,
            output_tokens=self.output_tokens,
            thinking_tokens=self.thinking_tokens,
            latency_ms=10,
        )

    async def submit_batch(
        self,
        model: str,
        items: list[BatchItem],
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        tier: str = "paid",
    ) -> str:
        job_id = f"fake_batch_{uuid.uuid4().hex[:12]}"
        results: list[ProviderResponse] = []
        for _item in items:
            raw = self.response_queue.pop(0) if self.response_queue else self.default_response
            results.append(
                ProviderResponse(
                    text=raw,
                    raw_output=raw,
                    input_tokens=self.input_tokens,
                    cached_tokens=self.cached_tokens,
                    output_tokens=self.output_tokens,
                    thinking_tokens=self.thinking_tokens,
                    latency_ms=10,
                )
            )
        self.batch_jobs[job_id] = results
        return job_id

    async def collect_batch(self, job_id: str) -> list[ProviderResponse]:
        if job_id not in self.batch_jobs:
            return []
        return self.batch_jobs[job_id]

    async def count_tokens(self, model: str, prompt: str) -> int:
        # Approximate 1 token per 4 characters or ~1.3 words
        words = len(prompt.split())
        return max(1, int(words * 1.3))
