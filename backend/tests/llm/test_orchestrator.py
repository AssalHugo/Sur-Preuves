"""Tests for central LLM orchestrator using FakeProvider."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from csc.llm.budget import BudgetManager
from csc.llm.cache import LocalLlmCache
from csc.llm.client import LlmClient
from csc.llm.exceptions import RealtimeDisallowedError, StructuredOutputError
from csc.llm.providers.fake import FakeProvider
from csc.llm.providers.registry import provider_registry


class SampleClaim(BaseModel):
    """Target output model for testing."""

    claim_text: str
    confidence: float
    is_factual: bool


@pytest.fixture(autouse=True)
def setup_fake_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    """Register fresh FakeProvider, isolated cache, and isolated budget manager."""
    fake = FakeProvider(
        default_response=SampleClaim(
            claim_text="Le mix électrique français est à plus de 90 % bas carbone.",
            confidence=0.98,
            is_factual=True,
        )
    )
    provider_registry.register("google", fake)
    provider_registry.register("gemini", fake)

    # Isolated cache directory
    test_cache = LocalLlmCache(cache_dir=tmp_path / "cache")
    monkeypatch.setattr("csc.llm.client.local_cache", test_cache)

    # Isolated budget manager to prevent test spend pollution in project files
    test_bm = BudgetManager(ledger_dir=tmp_path / "ledger")
    monkeypatch.setattr("csc.llm.client.budget_manager", test_bm)

    return fake


@pytest.mark.asyncio
async def test_llm_run_valid_structured_output(setup_fake_provider: FakeProvider) -> None:
    """llm.run returns validated Pydantic model with debug=True."""
    client = LlmClient()
    result = await client.run(
        prompt_id="_exemple",
        variables={"text": "Analyse de la production électrique"},
        output_model=SampleClaim,
        role="extraction",
        tier="paid",
        debug=True,
    )

    assert isinstance(result, SampleClaim)
    assert "90 % bas carbone" in result.claim_text
    assert result.confidence == 0.98
    assert result.is_factual is True


@pytest.mark.asyncio
async def test_llm_run_realtime_paid_disallowed_without_debug() -> None:
    """Paid tier realtime execution is disallowed without debug=True."""
    client = LlmClient()
    with pytest.raises(RealtimeDisallowedError):
        await client.run(
            prompt_id="_exemple",
            variables={"text": "Texte test"},
            output_model=SampleClaim,
            role="extraction",
            tier="paid",
            debug=False,
        )


@pytest.mark.asyncio
async def test_llm_run_invalid_output_retries_and_raises(setup_fake_provider: FakeProvider) -> None:
    """Invalid output triggers 1 retry and raises StructuredOutputError if still failing."""
    fake = setup_fake_provider
    fake.default_response = "Invalid non-JSON raw output"

    client = LlmClient()
    with pytest.raises(StructuredOutputError) as exc_info:
        await client.run(
            prompt_id="_exemple",
            variables={"text": "Texte test"},
            output_model=SampleClaim,
            role="extraction",
            tier="paid",
            debug=True,
        )

    assert "Structured output parsing failed after 2 attempts" in str(exc_info.value)
    assert len(fake.call_history) == 2  # Original call + 1 retry


@pytest.mark.asyncio
async def test_llm_run_invalid_first_valid_second_succeeds(
    setup_fake_provider: FakeProvider,
) -> None:
    """If first attempt is invalid but retry is valid, generation succeeds."""
    fake = setup_fake_provider
    fake.enqueue_response("Not a JSON object")
    fake.enqueue_response(
        SampleClaim(
            claim_text="Réponse valide après relance",
            confidence=0.95,
            is_factual=True,
        )
    )

    client = LlmClient()
    result = await client.run(
        prompt_id="_exemple",
        variables={"text": "Texte test"},
        output_model=SampleClaim,
        role="extraction",
        tier="paid",
        debug=True,
    )

    assert result.claim_text == "Réponse valide après relance"
    assert len(fake.call_history) == 2


@pytest.mark.asyncio
async def test_llm_run_cache_hit(setup_fake_provider: FakeProvider) -> None:
    """Identical subsequent calls return cached response without hitting provider."""
    fake = setup_fake_provider
    client = LlmClient()

    # First run (cache miss)
    res1 = await client.run(
        prompt_id="_exemple",
        variables={"text": "Proposition identique pour test de cache"},
        output_model=SampleClaim,
        role="extraction",
        tier="paid",
        debug=True,
    )
    assert len(fake.call_history) == 1

    # Second run (cache hit)
    res2 = await client.run(
        prompt_id="_exemple",
        variables={"text": "Proposition identique pour test de cache"},
        output_model=SampleClaim,
        role="extraction",
        tier="paid",
        debug=True,
    )
    assert len(fake.call_history) == 1  # Provider was NOT called again
    assert res1.claim_text == res2.claim_text


@pytest.mark.asyncio
async def test_llm_batch_workflow(setup_fake_provider: FakeProvider) -> None:
    """Batch submission and collection workflow works as expected."""
    client = LlmClient()
    items = [
        {"id": "claim_1", "text": "Proposition énergie 1"},
        {"id": "claim_2", "text": "Proposition énergie 2"},
    ]

    job = await client.submit_batch(
        prompt_id="_exemple",
        items=items,
        output_model=SampleClaim,
        role="extraction",
        tier="paid",
    )
    assert job.item_count == 2
    assert job.deferred_count == 0
    assert job.id == job.job_id
    assert job.prompt_id == "_exemple"
    assert len(job.prompt_sha) == 64

    # 1. Collect using job.id directly (L03 API contract: collect_batch(job.id))
    results = await client.collect_batch(
        job_id=job.id,
        output_model=SampleClaim,
        role="extraction",
        tier="paid",
        provider_name="google",
    )
    assert len(results) == 2
    assert all(isinstance(r, SampleClaim) for r in results)

    # 2. Collect using BatchJob object directly
    results2 = await client.collect_batch(
        job_id=job,
        output_model=SampleClaim,
        provider_name="google",
    )
    assert len(results2) == 2


def test_google_provider_thinking_config() -> None:
    """GoogleProvider must properly configure thinking_config for both generate and submit_batch."""
    from csc.llm.providers.google import GoogleProvider

    provider = GoogleProvider(api_key="fake_key_for_config_test")

    # 1. String thinking level (medium for synthesis)
    cfg_medium = provider._build_generate_config(params={"thinking": "medium"})
    assert cfg_medium.thinking_config is not None
    assert cfg_medium.thinking_config.thinking_level is not None
    assert cfg_medium.thinking_config.thinking_level.name == "MEDIUM"

    # 2. Integer thinking budget
    cfg_budget = provider._build_generate_config(params={"thinking": 1024})
    assert cfg_budget.thinking_config is not None
    assert cfg_budget.thinking_config.thinking_budget == 1024

    # 3. No thinking requested
    cfg_none = provider._build_generate_config(params={})
    assert cfg_none.thinking_config is None
