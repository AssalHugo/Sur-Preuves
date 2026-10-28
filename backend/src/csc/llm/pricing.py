"""Token pricing and dated tariff schedules for LLM inference."""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from csc.config import settings
from csc.contracts.enums import LlmTier


class PricingSchedule(BaseModel):
    """Tariff change effective from a specific date."""

    effective_date: date
    input_standard: float
    output_standard: float
    input_batch: float
    output_batch: float
    cached_standard: float = 0.0
    cached_batch: float = 0.0


class ModelPricing(BaseModel):
    """Pricing rates for a model per million tokens in USD."""

    input_standard: float
    output_standard: float
    input_batch: float
    output_batch: float
    cached_standard: float = 0.0
    cached_batch: float = 0.0
    schedule: list[PricingSchedule] = Field(default_factory=list)


class PricingConfig(BaseModel):
    """Global pricing configuration."""

    monthly_hard_cap_usd: float = 9.0
    models: dict[str, ModelPricing] = Field(default_factory=dict)


class PricingRegistry:
    """Calculates and estimates token inference costs with dated pricing support."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or settings.pricing_config_path
        self._config: PricingConfig | None = None

    def get_config(self) -> PricingConfig:
        if self._config is None:
            self.load()
        assert self._config is not None
        return self._config

    def load(self, path: Path | None = None) -> PricingConfig:
        target_path = path or self.config_path
        if not target_path.is_absolute():
            # Resolve relative to root if needed
            root = Path(__file__).resolve().parents[4]
            if (root / target_path).exists():
                target_path = root / target_path

        if not target_path.exists():
            # Fallback default
            self._config = PricingConfig()
            return self._config

        with open(target_path, encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        # Parse schedule date fields if needed
        models_dict: dict[str, Any] = {}
        for m_name, m_val in raw_data.get("models", {}).items():
            if isinstance(m_val, dict):
                schedules_raw = m_val.get("schedule", [])
                parsed_schedules: list[dict[str, Any]] = []
                for s in schedules_raw:
                    if isinstance(s, dict):
                        eff = s.get("effective_date")
                        if isinstance(eff, str):
                            eff_date = date.fromisoformat(eff)
                        elif isinstance(eff, (datetime, date)):
                            eff_date = eff if isinstance(eff, date) else eff.date()
                        else:
                            eff_date = date(2026, 1, 1)
                        s_copy = dict(s)
                        s_copy["effective_date"] = eff_date
                        parsed_schedules.append(s_copy)
                m_copy = dict(m_val)
                m_copy["schedule"] = parsed_schedules
                models_dict[m_name] = m_copy

        self._config = PricingConfig(
            monthly_hard_cap_usd=float(
                raw_data.get("monthly_hard_cap_usd", settings.llm_monthly_cap_usd)
            ),
            models=models_dict,
        )
        return self._config

    def get_rates(
        self,
        model: str,
        is_batch: bool = True,
        target_date: date | datetime | None = None,
        tier: str | LlmTier = LlmTier.PAID,
    ) -> tuple[float, float, float]:
        """Return (input_rate, output_rate, cached_rate) in USD per million tokens."""
        tier_val = tier.value if isinstance(tier, LlmTier) else str(tier)
        if tier_val.lower() == LlmTier.FREE.value:
            return 0.0, 0.0, 0.0

        config = self.get_config()
        model_pricing = config.models.get(model)
        if model_pricing is None:
            # Fallback to zero or default rates
            return 0.0, 0.0, 0.0

        # Check dated schedules
        eval_date: date
        if target_date is None:
            eval_date = date.today()
        elif isinstance(target_date, datetime):
            eval_date = target_date.date()
        else:
            eval_date = target_date

        input_rate = model_pricing.input_batch if is_batch else model_pricing.input_standard
        output_rate = model_pricing.output_batch if is_batch else model_pricing.output_standard
        cached_rate = model_pricing.cached_batch if is_batch else model_pricing.cached_standard

        if model_pricing.schedule:
            # Sort by effective_date ascending and pick latest <= eval_date
            matching = [s for s in model_pricing.schedule if s.effective_date <= eval_date]
            if matching:
                latest = max(matching, key=lambda s: s.effective_date)
                input_rate = latest.input_batch if is_batch else latest.input_standard
                output_rate = latest.output_batch if is_batch else latest.output_standard
                cached_rate = latest.cached_batch if is_batch else latest.cached_standard

        return input_rate, output_rate, cached_rate

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        thinking_tokens: int = 0,
        is_batch: bool = True,
        target_date: date | datetime | None = None,
        tier: str | LlmTier = LlmTier.PAID,
    ) -> float:
        """Calculate the real cost in USD for a given call."""
        tier_val = tier.value if isinstance(tier, LlmTier) else str(tier)
        if tier_val.lower() == LlmTier.FREE.value:
            return 0.0

        input_rate, output_rate, cached_rate = self.get_rates(
            model=model,
            is_batch=is_batch,
            target_date=target_date,
            tier=tier,
        )

        uncached_input = max(0, input_tokens - cached_tokens)
        input_cost = (uncached_input / 1_000_000.0) * input_rate
        cached_cost = (cached_tokens / 1_000_000.0) * cached_rate
        total_output = output_tokens + thinking_tokens
        output_cost = (total_output / 1_000_000.0) * output_rate

        return round(input_cost + cached_cost + output_cost, 8)

    def estimate_call_cost(
        self,
        model: str,
        input_tokens: int,
        max_output_tokens: int,
        is_batch: bool = True,
        target_date: date | datetime | None = None,
        tier: str | LlmTier = LlmTier.PAID,
    ) -> float:
        """Estimate the maximum cost of a call prior to execution."""
        return self.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=max_output_tokens,
            cached_tokens=0,
            thinking_tokens=0,
            is_batch=is_batch,
            target_date=target_date,
            tier=tier,
        )


pricing_registry = PricingRegistry()
