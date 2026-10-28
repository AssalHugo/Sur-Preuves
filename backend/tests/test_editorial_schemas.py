"""Tests de validation des schémas éditoriaux YAML et de leurs données d'exemple."""

from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_candidates_schema_and_sample() -> None:
    schema_file = Path("data/editorial/candidates.schema.yaml")
    sample_file = Path("data/editorial/candidates.sample.yaml")

    assert schema_file.exists()
    assert sample_file.exists()

    schema = _load_yaml(schema_file)
    data = _load_yaml(sample_file)

    # Doit valider sans erreur
    jsonschema.validate(instance=data, schema=schema)
    assert len(data["candidates"]) == 3


def test_candidates_schema_rejection() -> None:
    schema = _load_yaml(Path("data/editorial/candidates.schema.yaml"))

    # Slug invalide (majuscule et espaces)
    invalid_data = {
        "candidates": [
            {
                "slug": "Claire Delacroix",
                "name": "Claire Delacroix",
                "parties": ["PES"],
                "status": "declared",
            }
        ]
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_data, schema=schema)


def test_parties_schema_and_sample() -> None:
    schema_file = Path("data/editorial/parties.schema.yaml")
    sample_file = Path("data/editorial/parties.sample.yaml")

    assert schema_file.exists()
    assert sample_file.exists()

    schema = _load_yaml(schema_file)
    data = _load_yaml(sample_file)

    jsonschema.validate(instance=data, schema=schema)
    assert len(data["parties"]) == 3


def test_parties_schema_rejection() -> None:
    schema = _load_yaml(Path("data/editorial/parties.schema.yaml"))

    # Couleur hexadécimale invalide
    invalid_data = {
        "parties": [
            {
                "id": "PES",
                "name": "Parti Écologique",
                "short_name": "Écolo",
                "color_hex": "vert_pomme",
            }
        ]
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_data, schema=schema)


def test_groupes_partis_schema_and_samples() -> None:
    schema_file = Path("data/editorial/groupes_partis.schema.yaml")
    sample_file = Path("data/editorial/groupes_partis.sample.yaml")
    main_file = Path("data/editorial/groupes_partis.yaml")

    assert schema_file.exists()
    assert sample_file.exists()
    assert main_file.exists()

    schema = _load_yaml(schema_file)

    sample_data = _load_yaml(sample_file)
    jsonschema.validate(instance=sample_data, schema=schema)

    main_data = _load_yaml(main_file)
    jsonschema.validate(instance=main_data, schema=schema)

    assert len(sample_data["groups"]) == 3


def test_groupes_partis_schema_rejection() -> None:
    schema = _load_yaml(Path("data/editorial/groupes_partis.schema.yaml"))

    # Chambre invalide
    invalid_data = {
        "groups": [
            {
                "id": "GRP",
                "name": "Groupe Test",
                "short_name": "Test",
                "chamber": "conseil_economique",
                "associated_parties": ["PES"],
            }
        ]
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_data, schema=schema)
