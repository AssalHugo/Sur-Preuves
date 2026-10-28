"""Tests unitaires pour le bundle de publication (csc.contracts.publish)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from csc.contracts.enums import (
    CandidateStatus,
    ConsensusLevel,
    ReviewDecision,
    ReviewStatus,
    SentenceKind,
    Theme,
)
from csc.contracts.models import (
    Assessment,
    Candidate,
    Review,
    Sentence,
)
from csc.contracts.publish import (
    THEMES_CATALOG,
    AiDisclosure,
    PublicationBundle,
    export_bundle_schema,
    generate_bundle_schema,
)
from csc.contracts.uuid_v7 import uuid7


def test_themes_catalog_contains_all_15_themes() -> None:
    catalog_themes = {t.id for t in THEMES_CATALOG}
    enum_themes = set(Theme)
    assert catalog_themes == enum_themes
    assert len(THEMES_CATALOG) == 15

    for t in THEMES_CATALOG:
        assert len(t.label) > 0
        assert len(t.description) > 10


def test_ai_disclosure_defaults() -> None:
    disclosure = AiDisclosure()
    assert disclosure.ai_assisted is True
    assert "Gemini" in disclosure.statement
    assert disclosure.digital_source_type == "trainedAlgorithmicMedia"
    assert disclosure.methodology_url == "/methodologie/"


def test_bundle_rejects_unapproved_assessments() -> None:
    draft = Assessment(
        claim_id=uuid7(),
        status=ReviewStatus.AI_DRAFT,
        summary="Brouillon non validé",
        sentences=[
            Sentence(
                text="Phrase de contexte",
                kind=SentenceKind.CONTEXT,
                citations=[],
            )
        ],
    )

    with pytest.raises(ValidationError) as exc:
        PublicationBundle(
            candidates=[],
            themes=list(THEMES_CATALOG),
            assessments=[draft],
        )
    assert "ne peut contenir que des fiches au statut 'approved' ou 'published'" in str(exc.value)


def test_bundle_accepts_approved_assessments() -> None:
    rev_id = uuid7()
    ass_id = uuid7()
    item_id = uuid7()

    appr = Assessment(
        id=ass_id,
        claim_id=uuid7(),
        status=ReviewStatus.APPROVED,
        consensus_level=ConsensusLevel.STRONG,
        summary="Fiche validée",
        sentences=[
            Sentence(
                text="Phrase avec citation",
                kind=SentenceKind.STATEMENT,
                citations=[item_id],
            )
        ],
        reviews=[
            Review(
                assessment_id=ass_id,
                reviewer_id=rev_id,
                decision=ReviewDecision.APPROVED,
                comments="Validé",
            )
        ],
    )

    candidate = Candidate(
        slug="claire-delacroix",
        name="Claire Delacroix",
        parties=["PES"],
        status=CandidateStatus.DECLARED,
    )

    bundle = PublicationBundle(
        candidates=[candidate],
        themes=list(THEMES_CATALOG),
        assessments=[appr],
    )
    assert len(bundle.candidates) == 1
    assert len(bundle.assessments) == 1
    assert bundle.schema_version == "1.0.0"


def test_generate_and_export_bundle_schema(tmp_path: Path) -> None:
    schema = generate_bundle_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "properties" in schema
    assert "candidates" in schema["properties"]
    assert "assessments" in schema["properties"]

    out_file = tmp_path / "test_bundle.schema.json"
    exported_path = export_bundle_schema(out_file)
    assert exported_path.exists()

    content = json.loads(exported_path.read_text(encoding="utf-8"))
    assert content["$schema"] == "https://json-schema.org/draft/2020-12/schema"
