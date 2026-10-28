"""Données de fixtures pour les tests unitaires et d'intégration."""

from pathlib import Path

from csc.contracts.publish import PublicationBundle


def generate_sample_bundle() -> PublicationBundle:
    """Charge et valide le bundle de référence depuis les fixtures statiques."""
    fixture_path = Path("web/src/fixtures/bundle.sample.json")
    if not fixture_path.exists():
        # Repli si exécuté depuis backend/
        fixture_path = Path("../web/src/fixtures/bundle.sample.json")
    content = fixture_path.read_text(encoding="utf-8")
    return PublicationBundle.model_validate_json(content)
