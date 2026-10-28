"""LLM Layer module for civic-tech csc platform."""

from csc.llm.budget import BudgetManager, budget_manager
from csc.llm.cache import LocalLlmCache, local_cache
from csc.llm.client import BatchJob, LlmClient, llm
from csc.llm.exceptions import (
    BudgetExceededError,
    DataPrivacyError,
    DistinctModelPolicyError,
    DistinctProviderPolicyError,
    ImplicitCacheViolationError,
    LlmError,
    PolicyViolationError,
    PromptNotFoundError,
    RealtimeDisallowedError,
    StructuredOutputError,
)
from csc.llm.guardrails import validate_free_tier
from csc.llm.models_config import (
    EmbeddingConfig,
    ModelsConfiguration,
    PolicyConfig,
    RoleConfig,
    models_config_manager,
    pick_verifier,
    validate_configuration,
)
from csc.llm.pricing import PricingRegistry, pricing_registry
from csc.llm.prompts import PromptManager, PromptMetadata, prompt_manager
from csc.llm.providers.base import BatchItem, Provider, ProviderResponse
from csc.llm.providers.fake import FakeProvider
from csc.llm.providers.google import GoogleProvider
from csc.llm.providers.registry import ProviderRegistry, provider_registry

__all__ = [
    "BatchItem",
    "BatchJob",
    "BudgetExceededError",
    "BudgetManager",
    "DataPrivacyError",
    "DistinctModelPolicyError",
    "DistinctProviderPolicyError",
    "EmbeddingConfig",
    "FakeProvider",
    "GoogleProvider",
    "ImplicitCacheViolationError",
    "LlmClient",
    "LlmError",
    "LocalLlmCache",
    "ModelsConfiguration",
    "PolicyConfig",
    "PolicyViolationError",
    "PricingRegistry",
    "PromptManager",
    "PromptMetadata",
    "PromptNotFoundError",
    "Provider",
    "ProviderRegistry",
    "ProviderResponse",
    "RealtimeDisallowedError",
    "RoleConfig",
    "StructuredOutputError",
    "budget_manager",
    "llm",
    "local_cache",
    "models_config_manager",
    "pick_verifier",
    "pricing_registry",
    "prompt_manager",
    "provider_registry",
    "validate_configuration",
    "validate_free_tier",
]
