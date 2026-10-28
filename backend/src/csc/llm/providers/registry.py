"""Provider registry for plugging and retrieving LLM providers."""

from csc.llm.exceptions import LlmError
from csc.llm.providers.base import Provider
from csc.llm.providers.fake import FakeProvider
from csc.llm.providers.google import GoogleProvider


class ProviderRegistry:
    """Registry maintaining active provider adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        # Pre-register default providers
        self.register("google", GoogleProvider())
        self.register("gemini", GoogleProvider())
        self.register("fake", FakeProvider())

    def register(self, name: str, provider: Provider) -> None:
        """Register a provider implementation under a unique name."""
        self._providers[name.lower()] = provider

    def get(self, name: str) -> Provider:
        """Retrieve a registered provider by name."""
        p = self._providers.get(name.lower())
        if p is None:
            available = list(self._providers.keys())
            raise LlmError(f"LLM provider '{name}' is not registered. Available: {available}")
        return p


provider_registry = ProviderRegistry()
