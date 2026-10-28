"""Data privacy and free tier guardrails."""

import re
from typing import Any

from csc.llm.exceptions import DataPrivacyError

_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+33|0)[1-9](?:[\s.-]?\d{2}){4}\b")

_REVIEWER_KEYWORDS = [
    "relecteur",
    "reviewer",
    "avis_relecteur",
    "note_interne",
    "commentaire_interne",
    "eval_interne",
    "avis_expert",
]

_UNPUBLISHED_KEYWORDS = [
    "fiche non publiée",
    "fiche_non_publiee",
    "non_publie",
    "brouillon_interne",
    "internal_draft",
    "draft_unpublished",
    "confidentiel",
]


def _extract_text_content(val: Any) -> list[str]:
    """Recursively extract string values from nested structures."""
    texts: list[str] = []
    if isinstance(val, str):
        texts.append(val)
    elif isinstance(val, dict):
        for k, v in val.items():
            texts.append(str(k))
            texts.extend(_extract_text_content(v))
    elif isinstance(val, (list, tuple, set)):
        for item in val:
            texts.extend(_extract_text_content(item))
    return texts


def validate_free_tier(
    model: str,
    variables: dict[str, Any],
    is_public: bool = False,
) -> None:
    """Validate that input data meets free tier constraints.

    Google's free tier permits human review and model training on submitted inputs.
    Therefore, free tier calls must:
    1. Not target Gemini 4 Argon (paid only).
    2. Explicitly carry public=True or is_public=True.
    3. Exclude reviewer notes, personal data, and unpublished drafts.
    """
    if "argon" in model.lower():
        raise DataPrivacyError("Gemini 4 Argon does not have a free tier.")

    has_public_flag = (
        is_public or variables.get("public") is True or variables.get("is_public") is True
    )

    if not has_public_flag:
        raise DataPrivacyError(
            "Free tier only accepts inputs explicitly acknowledged as public (public=True). "
            "Google may use data sent via the free tier for model improvement and human review."
        )

    all_texts = _extract_text_content(variables)
    joined_text = " ".join(all_texts).lower()

    # Check for reviewer feedback keywords
    for kw in _REVIEWER_KEYWORDS:
        if kw in joined_text:
            raise DataPrivacyError(
                f"Free tier input rejected: sensitive reviewer note detected ('{kw}')."
            )

    # Check for unpublished content indicators
    for kw in _UNPUBLISHED_KEYWORDS:
        if kw in joined_text:
            raise DataPrivacyError(
                f"Free tier input rejected: unpublished/draft flag detected ('{kw}')."
            )

    # Check for personal information (emails or phone numbers)
    if _EMAIL_PATTERN.search(joined_text):
        raise DataPrivacyError("Free tier input rejected: personal data (email address) detected.")

    if _PHONE_PATTERN.search(joined_text):
        raise DataPrivacyError("Free tier input rejected: personal data (phone number) detected.")
