"""Tests de validation des fixtures JSON et du schéma de publication."""

import json
from pathlib import Path

import jsonschema

from csc.contracts.enums import ConsensusLevel, FactualVerdict, ReviewStatus
from csc.contracts.publish import PublicationBundle, generate_bundle_schema


def test_bundle_sample_json_validation_against_schema() -> None:
    schema_path = Path("web/src/schema/bundle.schema.json")
    fixtures_path = Path("web/src/fixtures/bundle.sample.json")

    assert schema_path.exists(), "web/src/schema/bundle.schema.json doit exister"
    assert fixtures_path.exists(), "web/src/fixtures/bundle.sample.json doit exister"

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    bundle_data = json.loads(fixtures_path.read_text(encoding="utf-8"))

    # 1. Validation jsonschema
    jsonschema.validate(instance=bundle_data, schema=schema)

    # 2. Validation Pydantic
    bundle = PublicationBundle.model_validate(bundle_data)
    assert bundle.schema_version == "1.0.0"


def test_bundle_sample_fixtures_coverage() -> None:
    fixtures_path = Path("web/src/fixtures/bundle.sample.json")
    bundle = PublicationBundle.model_validate_json(fixtures_path.read_text(encoding="utf-8"))

    # 3 candidats fictifs
    assert len(bundle.candidates) == 3
    candidate_slugs = {c.slug for c in bundle.candidates}
    assert candidate_slugs == {"claire-delacroix", "alexandre-leroy", "mariam-diallo"}

    # 15 thèmes
    assert len(bundle.themes) == 15

    # 10 fiches d'évaluation
    assert len(bundle.assessments) == 10

    # Toutes les fiches sont approuvées avec au moins une relecture approuvée
    for ass in bundle.assessments:
        assert ass.status == ReviewStatus.APPROVED
        assert len(ass.reviews) >= 1
        assert any(r.decision.value == "approved" for r in ass.reviews)
        assert len(ass.sentences) >= 2

    # Vérification de la couverture exhaustive des 10 verdicts (5 factuels + 5 consensus causaux)
    factual_verdicts = {
        ass.factual_verdict.value for ass in bundle.assessments if ass.factual_verdict is not None
    }
    expected_factual = {v.value for v in FactualVerdict}
    assert factual_verdicts == expected_factual, "Tous les verdicts factuels doivent être couverts"

    consensus_levels = {
        ass.consensus_level.value for ass in bundle.assessments if ass.consensus_level is not None
    }
    expected_consensus = {c.value for c in ConsensusLevel}
    assert consensus_levels == expected_consensus, (
        "Tous les niveaux de consensus doivent être couverts"
    )

    total_verdicts = [
        ass.factual_verdict.value if ass.factual_verdict else ass.consensus_level.value  # type: ignore[union-attr]
        for ass in bundle.assessments
    ]
    assert len(set(total_verdicts)) == 10, "Les 10 fiches doivent couvrir 10 verdicts distincts"


def test_generated_schema_matches_exported_file() -> None:
    schema_path = Path("web/src/schema/bundle.schema.json")
    expected_schema = generate_bundle_schema()
    on_disk_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert on_disk_schema == expected_schema


def test_fixture_generator_in_memory() -> None:
    from tests.sample_data import generate_sample_bundle

    bundle = generate_sample_bundle()
    assert len(bundle.candidates) == 3
    assert len(bundle.assessments) == 10
    assert bundle.schema_version == "1.0.0"
