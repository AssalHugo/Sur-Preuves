"""Models configuration and verification policy enforcement."""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from csc.config import settings
from csc.llm.exceptions import DistinctModelPolicyError, DistinctProviderPolicyError

logger = logging.getLogger(__name__)


class RoleConfig(BaseModel):
    """Configuration for a specific LLM pipeline role."""

    provider: str = "google"
    model: str
    batch: bool = True
    thinking: str | None = None
    max_output_tokens: int = 4096
    temperature: float = 0.0
    fallback: str | None = None


class PolicyConfig(BaseModel):
    """Policy rules for model selection and cross-verification."""

    require_distinct_verification_model: bool = True
    require_distinct_verification_provider: bool = False


class EmbeddingConfig(BaseModel):
    """Configuration for local CPU embeddings."""

    provider: str = "local"
    model: str = "intfloat/multilingual-e5-large"
    dimension: int = 1024
    dev_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    dev_dimension: int = 384


class ModelsConfiguration(BaseModel):
    """Complete models configuration parsed from config/models.yaml."""

    roles: dict[str, RoleConfig] = Field(default_factory=dict)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    verification_overrides: dict[str, str] = Field(default_factory=dict)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)


class ModelsConfigManager:
    """Manages loading and resolving models configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or settings.models_config_path
        self._config: ModelsConfiguration | None = None
        self._warned_same_provider: bool = False

    def get_config(self) -> ModelsConfiguration:
        if self._config is None:
            self.load()
        assert self._config is not None
        return self._config

    def load(self, path: Path | None = None) -> ModelsConfiguration:
        target_path = path or self.config_path
        if not target_path.is_absolute():
            root = Path(__file__).resolve().parents[4]
            if (root / target_path).exists():
                target_path = root / target_path

        if not target_path.exists():
            self._config = ModelsConfiguration()
            return self._config

        with open(target_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        # Parse roles
        roles_dict: dict[str, Any] = {}
        for r_name, r_val in raw.get("roles", {}).items():
            if isinstance(r_val, dict):
                roles_dict[r_name] = r_val

        # Parse embedding
        embedding_raw = raw.get("embedding", {})
        embedding_cfg = (
            EmbeddingConfig(**embedding_raw)
            if isinstance(embedding_raw, dict)
            else EmbeddingConfig()
        )

        # Parse policy
        policy_raw = raw.get("policy", {})
        policy_cfg = PolicyConfig(**policy_raw) if isinstance(policy_raw, dict) else PolicyConfig()

        # Parse verification overrides
        overrides = raw.get("verification_overrides", {})

        self._config = ModelsConfiguration(
            roles=roles_dict,
            embedding=embedding_cfg,
            verification_overrides=overrides if isinstance(overrides, dict) else {},
            policy=policy_cfg,
        )
        return self._config

    def pick_verifier(
        self, synth_model: str, config: ModelsConfiguration | None = None
    ) -> tuple[str, str]:
        """Resolve (verifier_provider, verifier_model) for a given synthesis model.

        Raises DistinctModelPolicyError if policy mandates distinct models and resolved verifier
        matches synth_model.
        """
        cfg = config or self.get_config()
        verifier_role = cfg.roles.get(
            "verification", RoleConfig(provider="google", model="gemini-3.5-flash-lite")
        )

        verifier_provider = verifier_role.provider
        if synth_model in cfg.verification_overrides:
            verifier_model = cfg.verification_overrides[synth_model]
        else:
            verifier_model = verifier_role.model

        if cfg.policy.require_distinct_verification_model and verifier_model == synth_model:
            raise DistinctModelPolicyError(
                f"Verification model '{verifier_model}' cannot be identical to synthesis model "
                f"'{synth_model}' under strict verification policy."
            )

        synth_provider = cfg.roles.get("synthesis", RoleConfig(model="")).provider
        if (
            cfg.policy.require_distinct_verification_provider
            and verifier_provider == synth_provider
        ):
            raise DistinctProviderPolicyError(
                f"Verification provider '{verifier_provider}' cannot be identical to "
                f"synthesis provider '{synth_provider}' under strict provider diversity policy."
            )

        if (
            not cfg.policy.require_distinct_verification_provider
            and verifier_provider == synth_provider
        ):
            if not self._warned_same_provider:
                logger.warning(
                    "Verification and synthesis use the same provider ('%s'). "
                    "same_provider=true will be recorded in audit logs.",
                    verifier_provider,
                )
                self._warned_same_provider = True

        return verifier_provider, verifier_model

    def validate_configuration(self, config: ModelsConfiguration | None = None) -> list[str]:
        """Validate model setup on startup and return collected warnings.

        Refuses to start if synthesis.model or synthesis_simple.model equals their verifier.
        """
        cfg = config or self.get_config()
        warnings: list[str] = []

        if "synthesis" in cfg.roles:
            synth_model = cfg.roles["synthesis"].model
            prov, v_model = self.pick_verifier(synth_model, cfg)
            if prov == cfg.roles["synthesis"].provider:
                warnings.append(
                    f"Synthesis role '{synth_model}' and verifier '{v_model}' "
                    f"share provider '{prov}'."
                )

        if "synthesis_simple" in cfg.roles:
            simple_model = cfg.roles["synthesis_simple"].model
            prov, v_model = self.pick_verifier(simple_model, cfg)
            if prov == cfg.roles["synthesis_simple"].provider:
                warnings.append(
                    f"Synthesis simple role '{simple_model}' and verifier '{v_model}' "
                    f"share provider '{prov}'."
                )

        return warnings


models_config_manager = ModelsConfigManager()


def pick_verifier(synth_model: str, config: ModelsConfiguration | None = None) -> tuple[str, str]:
    """Helper shortcut for pick_verifier."""
    return models_config_manager.pick_verifier(synth_model, config)


def validate_configuration(config: ModelsConfiguration | None = None) -> list[str]:
    """Helper shortcut for validate_configuration."""
    return models_config_manager.validate_configuration(config)
