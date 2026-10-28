"""Exceptions for the LLM subsystem."""


class LlmError(Exception):
    """Base exception for all LLM errors."""


class BudgetExceededError(LlmError):
    """Raised when an operation would exceed the configured monthly budget cap."""


class PolicyViolationError(LlmError):
    """Raised when a model routing or verification policy is violated."""


class DistinctModelPolicyError(PolicyViolationError):
    """Raised when the verification model is identical to the synthesis model."""


class DistinctProviderPolicyError(PolicyViolationError):
    """Raised when verification and synthesis providers are required to be distinct."""


class DataPrivacyError(LlmError):
    """Raised when private or unverified data is submitted to the free tier."""


class RealtimeDisallowedError(LlmError):
    """Raised when a realtime call is attempted on paid tier without debug mode."""


class StructuredOutputError(LlmError):
    """Raised when LLM output cannot be parsed into the expected structured model."""


class PromptNotFoundError(LlmError):
    """Raised when a requested prompt template cannot be found."""


class ImplicitCacheViolationError(LlmError):
    """Raised when a prompt template places variables before the stable cache prefix."""
