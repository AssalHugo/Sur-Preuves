"""Tests for prompt loading, Jinja2 rendering, and implicit cache prefix validation."""

import pytest

from csc.llm.exceptions import ImplicitCacheViolationError, PromptNotFoundError
from csc.llm.prompts import PromptMetadata, PromptTemplate, prompt_manager


def test_load_and_render_exemple_prompt() -> None:
    """The reference prompt _exemple.md must load with metadata and render correctly."""
    template = prompt_manager.get_template("_exemple")
    assert template.metadata.id == "_exemple"
    assert template.metadata.version == "1.0.0"
    assert template.metadata.role == "extraction"
    assert len(template.sha256) == 64

    # Verify that the preamble complies with implicit cache prefix requirement
    template.validate_cache_prefix()

    rendered, version, sha = prompt_manager.render(
        "_exemple",
        {"text": "Augmentation du budget de la recherche de 2 milliards d'euros."},
    )
    assert "Directives d'extraction scientifique" in rendered
    assert "Augmentation du budget de la recherche" in rendered
    assert version == "1.0.0"
    assert sha == template.sha256


def test_prompt_not_found_raises() -> None:
    """Requesting an unexisting prompt should raise PromptNotFoundError."""
    with pytest.raises(PromptNotFoundError):
        prompt_manager.get_template("non_existent_prompt_xyz")


def test_implicit_cache_prefix_violation() -> None:
    """A prompt template with dynamic variables before the stable prefix must fail validation."""
    meta = PromptMetadata(id="bad_prompt", min_prefix_tokens=50)
    bad_template = PromptTemplate(
        metadata=meta,
        raw_body="Texte court {{ var }} suivi de longues instructions...",
        sha256="abc",
        path=prompt_manager.prompts_dir / "bad.md",
    )

    with pytest.raises(ImplicitCacheViolationError) as exc_info:
        bad_template.validate_cache_prefix()

    assert "places dynamic variables after only" in str(exc_info.value)
