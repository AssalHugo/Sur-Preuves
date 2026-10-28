"""Tests de la CLI csc hal."""

from typing import Any

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from csc.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@respx.mock
def test_cli_hal_search_nominal(runner: CliRunner, load_hal_cassette: Any) -> None:
    cassette = load_hal_cassette("search_proximity")
    respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    result = runner.invoke(
        app,
        [
            "hal",
            "search",
            "taxe carbone",
            "--proximity",
            "taxe,carbone,3",
            "--limit",
            "5",
        ],
    )

    assert result.exit_code == 0
    assert "Recherche HAL" in result.stdout
    assert "taxe carbone" in result.stdout
    assert "Résultats HAL (5 publications)" in result.stdout
    assert "Fallait-il" in result.stdout
    assert "halshs-00557065" in result.stdout


def test_cli_hal_search_invalid_proximity(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["hal", "search", "taxe", "--proximity", "invalide"],
    )
    assert result.exit_code == 1
    assert "Format de proximité invalide" in result.stdout


@respx.mock
def test_cli_hal_structure_nominal(runner: CliRunner, load_hal_cassette: Any) -> None:
    cassette = load_hal_cassette("search_structure")
    respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    result = runner.invoke(
        app,
        ["hal", "structure", "IPP", "--query", "carbone", "--limit", "5"],
    )

    assert result.exit_code == 0
    assert "Recherche HAL par structure : IPP (ID 266522)" in result.stdout
    assert "Publications IPP (ID 266522)" in result.stdout


def test_cli_hal_structure_unknown(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["hal", "structure", "INCONNU_1234"],
    )
    assert result.exit_code == 1
    assert "Structure invalide" in result.stdout


@respx.mock
def test_cli_hal_get_nominal(runner: CliRunner, load_hal_cassette: Any) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    result = runner.invoke(
        app,
        ["hal", "get", "halshs-03386384"],
    )

    assert result.exit_code == 0
    assert "Consultation de la publication HAL : halshs-03386384" in result.stdout
    assert "Pilotage stratégique de la taxe carbone" in result.stdout
    assert "halshs-03386384" in result.stdout
    assert "10.3917/mav.124.0151" in result.stdout
    assert "Marco Heimann" in result.stdout


@respx.mock
def test_cli_hal_get_not_found(runner: CliRunner, load_hal_cassette: Any) -> None:
    cassette = load_hal_cassette("empty_search")
    respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    result = runner.invoke(
        app,
        ["hal", "get", "hal-inexistant"],
    )
    assert result.exit_code == 1
    assert "Publication introuvable" in result.stdout


def test_cli_hal_structures_list(runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["hal", "structures"],
    )
    assert result.exit_code == 0
    assert "Référentiel des structures de recherche utiles" in result.stdout
    assert "IPP" in result.stdout
    assert "266522" in result.stdout
    assert "OFCE" in result.stdout
    assert "250936" in result.stdout
    assert "INRAE" in result.stdout
    assert "577435" in result.stdout
    assert "LIEPP" in result.stdout
    assert "218465" in result.stdout
