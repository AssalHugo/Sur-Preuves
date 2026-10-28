"""Tests for free tier privacy guardrails and sensitive data rejection."""

import pytest

from csc.llm.exceptions import DataPrivacyError
from csc.llm.guardrails import validate_free_tier


def test_free_tier_rejects_argon() -> None:
    """Gemini 4 Argon does not offer a free tier."""
    with pytest.raises(DataPrivacyError) as exc_info:
        validate_free_tier(
            model="gemini-4-argon",
            variables={"text": "Contenu public"},
            is_public=True,
        )
    assert "Gemini 4 Argon does not have a free tier" in str(exc_info.value)


def test_free_tier_requires_public_flag() -> None:
    """Free tier calls must carry explicit public=True acknowledgment."""
    with pytest.raises(DataPrivacyError) as exc_info:
        validate_free_tier(
            model="gemini-3.5-flash-lite",
            variables={"text": "Programme officiel public"},
            is_public=False,
        )
    assert "public=True" in str(exc_info.value)


def test_free_tier_rejects_reviewer_notes() -> None:
    """Calls containing internal reviewer notes must be rejected."""
    with pytest.raises(DataPrivacyError) as exc_info:
        validate_free_tier(
            model="gemini-3.5-flash-lite",
            variables={"text": "Texte avec avis_relecteur confidentiel"},
            is_public=True,
        )
    assert "sensitive reviewer note" in str(exc_info.value)


def test_free_tier_rejects_unpublished_drafts() -> None:
    """Calls referencing unpublished drafts must be rejected."""
    with pytest.raises(DataPrivacyError) as exc_info:
        validate_free_tier(
            model="gemini-3.5-flash-lite",
            variables={"metadata": {"status": "fiche non publiée"}},
            is_public=True,
        )
    assert "unpublished/draft flag" in str(exc_info.value)


def test_free_tier_rejects_personal_data() -> None:
    """Calls containing emails or phone numbers must be rejected."""
    with pytest.raises(DataPrivacyError) as exc_info:
        validate_free_tier(
            model="gemini-3.5-flash-lite",
            variables={"contact": "expert@cnrs.fr"},
            is_public=True,
        )
    assert "personal data" in str(exc_info.value)


def test_free_tier_accepts_clean_public_data() -> None:
    """Clean public data marked with is_public=True should be accepted."""
    validate_free_tier(
        model="gemini-3.5-flash-lite",
        variables={"text": "Rapport GIEC 2023 sur les émissions de gaz à effet de serre."},
        is_public=True,
    )
