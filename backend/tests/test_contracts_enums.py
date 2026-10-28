"""Tests unitaires pour les énumérations métier (csc.contracts.enums)."""

from csc.contracts.enums import (
    CandidateStatus,
    CitationSupportVerdict,
    ClaimType,
    ConsensusLevel,
    EvidenceDirection,
    FactualVerdict,
    LlmTier,
    RectificationStatus,
    ReviewDecision,
    ReviewStatus,
    SentenceKind,
    SmsLevel,
    SourceKind,
    Theme,
    VotePosition,
)


def test_claim_type_values() -> None:
    assert ClaimType.NORMATIVE.value == "normative"
    assert ClaimType.FACTUAL.value == "factual"
    assert ClaimType.CAUSAL.value == "causal"
    assert len(ClaimType) == 3


def test_factual_verdict_values() -> None:
    expected = {"accurate", "approximate", "misleading", "inaccurate", "unverifiable"}
    assert {v.value for v in FactualVerdict} == expected
    assert len(FactualVerdict) == 5


def test_evidence_direction_values() -> None:
    expected = {"supports", "mixed", "contradicts", "inconclusive"}
    assert {v.value for v in EvidenceDirection} == expected
    assert len(EvidenceDirection) == 4


def test_consensus_level_values() -> None:
    expected = {
        "strong",
        "emerging",
        "contested",
        "insufficient_evidence",
        "novel_no_ex_post",
    }
    assert {v.value for v in ConsensusLevel} == expected
    assert len(ConsensusLevel) == 5


def test_sms_level_values() -> None:
    assert SmsLevel.LEVEL_1.value == 1
    assert SmsLevel.LEVEL_5.value == 5
    assert int(SmsLevel.LEVEL_1) == 1
    assert [int(lvl) for lvl in SmsLevel] == [1, 2, 3, 4, 5]


def test_themes_taxonomy_has_15_themes() -> None:
    expected_themes = {
        "economie-emploi",
        "fiscalite",
        "retraites",
        "sante",
        "education",
        "energie",
        "climat",
        "agriculture",
        "logement",
        "securite-justice",
        "immigration",
        "transport",
        "numerique",
        "institutions",
        "europe-international",
    }
    assert {t.value for t in Theme} == expected_themes
    assert len(Theme) == 15


def test_review_status_lifecycle() -> None:
    expected = {
        "ai_draft",
        "in_review",
        "changes_requested",
        "approved",
        "published",
        "withdrawn",
    }
    assert {s.value for s in ReviewStatus} == expected


def test_source_kind_values() -> None:
    expected = {
        "programme",
        "profession_de_foi",
        "amendment",
        "vote",
        "scholarly_work",
        "institutional_report",
    }
    assert {k.value for k in SourceKind} == expected


def test_additional_enums() -> None:
    assert CandidateStatus.DECLARED.value == "declared"
    assert CandidateStatus.OFFICIAL.value == "official"

    assert SentenceKind.CONTEXT.value == "context"
    assert SentenceKind.STATEMENT.value == "statement"

    assert ReviewDecision.APPROVED.value == "approved"
    assert ReviewDecision.CHANGES_REQUESTED.value == "changes_requested"
    assert ReviewDecision.REJECTED.value == "rejected"

    assert CitationSupportVerdict.SUPPORTED.value == "supported"
    assert LlmTier.PAID.value == "paid"
    assert LlmTier.FREE.value == "free"

    assert RectificationStatus.RECEIVED.value == "received"
    assert VotePosition.POUR.value == "pour"
