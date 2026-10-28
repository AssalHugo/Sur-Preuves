"""Tests for pricing engine and dated tariff schedules."""

from datetime import date

from csc.contracts.enums import LlmTier
from csc.llm.pricing import PricingRegistry


def test_pricing_registry_dated_argon_schedule() -> None:
    """Gemini 4 Argon batch pricing must double on 2026-12-01."""
    pricing = PricingRegistry()

    # Before December 1st, 2026: 1.0 $ / 5.0 $ per million
    pre_date = date(2026, 11, 20)
    in_rate_pre, out_rate_pre, cached_rate_pre = pricing.get_rates(
        "gemini-4-argon", is_batch=True, target_date=pre_date
    )
    assert in_rate_pre == 1.0
    assert out_rate_pre == 5.0
    assert cached_rate_pre == 0.10

    # On / After December 1st, 2026: 2.0 $ / 10.0 $ per million (x2)
    post_date = date(2026, 12, 1)
    in_rate_post, out_rate_post, cached_rate_post = pricing.get_rates(
        "gemini-4-argon", is_batch=True, target_date=post_date
    )
    assert in_rate_post == 2.0
    assert out_rate_post == 10.0
    assert cached_rate_post == 0.20


def test_pricing_registry_dated_flash38_schedule() -> None:
    """Gemini 3.8 Flash batch pricing must double on 2027-01-01."""
    pricing = PricingRegistry()

    # In December 2026: 0.15 $ / 1.25 $ per million
    pre_date = date(2026, 12, 25)
    in_rate_pre, out_rate_pre, _ = pricing.get_rates(
        "gemini-3.8-flash", is_batch=True, target_date=pre_date
    )
    assert in_rate_pre == 0.15
    assert out_rate_pre == 1.25

    # On / After January 1st, 2027: 0.30 $ / 2.50 $ per million (x2)
    post_date = date(2027, 1, 1)
    in_rate_post, out_rate_post, _ = pricing.get_rates(
        "gemini-3.8-flash", is_batch=True, target_date=post_date
    )
    assert in_rate_post == 0.30
    assert out_rate_post == 2.50


def test_pricing_free_tier_zero_cost() -> None:
    """Free tier calls must always incur 0.0 USD cost."""
    pricing = PricingRegistry()
    cost = pricing.calculate_cost(
        model="gemini-3.5-flash-lite",
        input_tokens=100000,
        output_tokens=50000,
        tier=LlmTier.FREE,
    )
    assert cost == 0.0


def test_pricing_calculation_with_thinking_and_cached() -> None:
    """Thinking tokens are charged at output rate and cached tokens at cached rate."""
    pricing = PricingRegistry()

    # Model: gemini-3.5-flash-lite batch
    # input_batch = 0.075, output_batch = 0.625, cached_batch = 0.01875
    # input: 10_000, of which 4_000 are cached -> 6_000 uncached at 0.075, 4_000 at 0.01875
    # output: 2_000, thinking: 1_000 -> 3_000 at 0.625
    cost = pricing.calculate_cost(
        model="gemini-3.5-flash-lite",
        input_tokens=10_000,
        output_tokens=2_000,
        cached_tokens=4_000,
        thinking_tokens=1_000,
        is_batch=True,
    )
    expected_uncached = (6_000 / 1_000_000) * 0.075
    expected_cached = (4_000 / 1_000_000) * 0.01875
    expected_out = (3_000 / 1_000_000) * 0.625
    expected_total = round(expected_uncached + expected_cached + expected_out, 8)

    assert cost == expected_total
    assert cost < 0.01
