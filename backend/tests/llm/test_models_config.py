"""Tests for models configuration, verification policy, and routing."""

import pytest

from csc.llm.exceptions import DistinctModelPolicyError
from csc.llm.models_config import (
    ModelsConfiguration,
    PolicyConfig,
    RoleConfig,
    models_config_manager,
    pick_verifier,
    validate_configuration,
)


def test_default_models_config_loads() -> None:
    """The default models.yaml configuration should be valid and specify distinct models."""
    cfg = models_config_manager.load()
    assert "synthesis" in cfg.roles
    assert "verification" in cfg.roles
    assert cfg.roles["synthesis"].model == "gemini-4-argon"
    assert cfg.roles["verification"].model == "gemini-3.5-flash-lite"

    # Verifier for gemini-4-argon should be gemini-3.5-flash-lite
    prov, v_model = pick_verifier("gemini-4-argon", cfg)
    assert v_model == "gemini-3.5-flash-lite"
    assert v_model != "gemini-4-argon"

    # Verifier for gemini-3.5-flash-lite must be routed to gemini-3.1-flash-lite via override
    prov_simple, v_model_simple = pick_verifier("gemini-3.5-flash-lite", cfg)
    assert v_model_simple == "gemini-3.1-flash-lite"
    assert v_model_simple != "gemini-3.5-flash-lite"

    warnings = validate_configuration(cfg)
    assert isinstance(warnings, list)


def test_distinct_model_policy_rejection() -> None:
    """Startup must fail if synthesis and verification share the same model without override."""
    invalid_config = ModelsConfiguration(
        roles={
            "synthesis": RoleConfig(provider="google", model="gemini-3.5-flash-lite"),
            "verification": RoleConfig(provider="google", model="gemini-3.5-flash-lite"),
        },
        verification_overrides={},  # No override provided
        policy=PolicyConfig(require_distinct_verification_model=True),
    )

    with pytest.raises(DistinctModelPolicyError) as exc_info:
        pick_verifier("gemini-3.5-flash-lite", invalid_config)

    assert "cannot be identical" in str(exc_info.value)

    with pytest.raises(DistinctModelPolicyError):
        validate_configuration(invalid_config)
