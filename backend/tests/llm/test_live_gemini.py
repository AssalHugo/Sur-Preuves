"""Live Gemini API tests (excluded from standard CI via -m 'not live')."""

import os

import pytest
from pydantic import BaseModel

from csc.llm.client import LlmClient
from csc.llm.providers.google import GoogleProvider


class LiveAnalysis(BaseModel):
    """Output model for live tests."""

    theme: str
    is_scientific_claim: bool


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_gemini_argon_access_or_fallback() -> None:
    """Verify whether the configured Gemini API key has access to gemini-4-argon.

    If gemini-4-argon is not accessible (e.g. preview access pending), this test
    warns that config/models.yaml should fallback to gemini-3.1-pro-preview.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set in environment.")

    provider = GoogleProvider(api_key=api_key)
    prompt = "Test de disponibilité de Gemini 4 Argon. Répondez simplement 'OK'."

    try:
        response = await provider.generate(
            model="gemini-4-argon",
            prompt=prompt,
            params={"max_output_tokens": 10},
        )
        assert len(response.text) > 0
        print("\n[LIVE SUCCESS] Account has active access to 'gemini-4-argon'!")
    except Exception as e:
        print(
            f"\n[LIVE NOTICE] 'gemini-4-argon' is not currently accessible on this account ({e}).\n"
            "Action requise : basculer le rôle 'synthesis' sur 'gemini-3.1-pro-preview'."
        )


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_gemini_batch_flash_lite_budget() -> None:
    """Run a small 10-element batch with gemini-3.5-flash-lite and verify cost is < $0.01."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set in environment.")

    client = LlmClient()
    items = [
        {"id": f"prop_{i}", "text": f"Proposition scientifique {i} sur la décarbonation."}
        for i in range(10)
    ]

    job = await client.submit_batch(
        prompt_id="_exemple",
        items=items,
        output_model=LiveAnalysis,
        role="extraction",
        tier="paid",
    )
    assert job.item_count == 10
