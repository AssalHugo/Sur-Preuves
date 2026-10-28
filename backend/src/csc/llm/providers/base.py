"""Abstract provider interface and response protocols."""

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """Raw generation response returned by an underlying provider."""

    text: str = ""
    raw_output: str = ""
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    latency_ms: int = 0


class BatchItem(BaseModel):
    """Single item in a batch generation payload."""

    custom_id: str
    prompt: str
    params: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Provider(Protocol):
    """Protocol that all LLM execution backends must implement."""

    async def generate(
        self,
        model: str,
        prompt: str,
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        tier: str = "paid",
    ) -> ProviderResponse:
        """Execute a single synchronous or realtime text generation."""
        ...

    async def submit_batch(
        self,
        model: str,
        items: list[BatchItem],
        schema: type[BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        tier: str = "paid",
    ) -> str:
        """Submit an asynchronous batch job and return the unique job identifier."""
        ...

    async def collect_batch(self, job_id: str) -> list[ProviderResponse]:
        """Fetch and return results for a previously submitted batch job."""
        ...

    async def count_tokens(self, model: str, prompt: str) -> int:
        """Count or approximate input tokens for a given prompt string."""
        ...
