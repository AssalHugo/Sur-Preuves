"""Tests d'acceptation de la CLI pour le connecteur OpenAlex."""

from typing import Any

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from csc.cli import app
from csc.connectors.openalex import get_default_client


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@respx.mock
def test_cli_openalex_search_reviews_only_acceptance(runner: CliRunner, load_cassette: Any) -> None:
    """Critère d'acceptation :

    CLI : `csc openalex search "carbon tax employment" --reviews-only` affiche 10 résultats triés.
    """
    cassette = load_cassette("reviews_search")
    respx.get("https://api.openalex.org/works").mock(
        return_value=Response(
            200,
            json=cassette,
            headers={
                "x-ratelimit-credits-used": "1.0",
                "x-ratelimit-remaining": "99990",
                "x-ratelimit-limit": "100000",
            },
        )
    )

    result = runner.invoke(
        app,
        ["openalex", "search", "carbon tax employment", "--reviews-only"],
    )

    assert result.exit_code == 0
    assert "Recherche OpenAlex : carbon tax employment" in result.stdout
    assert "revues systématiques uniquement" in result.stdout
    assert "Résultats OpenAlex (10 publications)" in result.stdout

    # Vérification de la présence des 10 fiches de revues
    for i in range(10):
        assert f"Systematic review #{i + 1}" in result.stdout
        assert "Oui" in result.stdout


@respx.mock
def test_cli_openalex_search_nominal(runner: CliRunner, load_cassette: Any) -> None:
    cassette = load_cassette("works_search")
    respx.get("https://api.openalex.org/works").mock(return_value=Response(200, json=cassette))

    result = runner.invoke(
        app,
        ["openalex", "search", "carbon tax", "--limit", "5"],
    )

    assert result.exit_code == 0
    assert "Résultats OpenAlex (5 publications)" in result.stdout
    assert "Study on carbon tax" in result.stdout


@respx.mock
def test_cli_openalex_get_work(runner: CliRunner, load_cassette: Any) -> None:
    cassette = load_cassette("single_work")
    respx.get("https://api.openalex.org/works/https://doi.org/10.1038/s41558-019-0401-7").mock(
        return_value=Response(200, json=cassette)
    )

    result = runner.invoke(
        app,
        ["openalex", "get", "10.1038/s41558-019-0401-7"],
    )

    assert result.exit_code == 0
    assert "Measuring the macroeconomic impact of carbon taxes" in result.stdout
    assert "Gilbert E. Metcalf, James H. Stock" in result.stdout
    assert "Nature Climate Change" in result.stdout
    assert "412" in result.stdout


@respx.mock
def test_cli_openalex_institutions(runner: CliRunner, load_cassette: Any) -> None:
    cassette = load_cassette("institutions")
    respx.get("https://api.openalex.org/institutions").mock(
        return_value=Response(200, json=cassette)
    )

    result = runner.invoke(
        app,
        ["openalex", "institutions", "T11636", "--limit", "3"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "Top Institutions OpenAlex (3)" in result.stdout
    assert "Harvard University" in result.stdout
    assert "University of Cambridge" in result.stdout
    assert "CNRS" in result.stdout


@respx.mock
def test_cli_openalex_authors(runner: CliRunner, load_cassette: Any) -> None:
    cassette = load_cassette("authors")
    respx.get("https://api.openalex.org/authors").mock(return_value=Response(200, json=cassette))

    result = runner.invoke(
        app,
        ["openalex", "authors", "T11636", "--limit", "3"],
        env={"COLUMNS": "160"},
    )

    assert result.exit_code == 0
    assert "Top Chercheurs OpenAlex (3)" in result.stdout
    assert "Gilbert E. Metcalf" in result.stdout
    assert "Tufts University" in result.stdout


def test_cli_openalex_budget(runner: CliRunner) -> None:
    client = get_default_client()
    client.budget_manager.reset()

    result = runner.invoke(app, ["openalex", "budget"])

    assert result.exit_code == 0
    assert "Budget journalier OpenAlex" in result.stdout
    assert "100000.0 crédits" in result.stdout
    assert "Seuil d'arrêt propre (90 %)" in result.stdout
    assert "Budget opérationnel" in result.stdout


@respx.mock
def test_cli_openalex_search_semantic(runner: CliRunner, load_cassette: Any) -> None:
    cassette = load_cassette("works_search")
    respx.get("https://api.openalex.org/works").mock(return_value=Response(200, json=cassette))

    result = runner.invoke(
        app,
        ["openalex", "search", "impact of environmental taxes", "--semantic", "--limit", "3"],
    )

    assert result.exit_code == 0
    assert "recherche sémantique" in result.stdout
    assert "Résultats OpenAlex (3 publications)" in result.stdout


@respx.mock
def test_cli_openalex_get_work_markup_safety(runner: CliRunner) -> None:
    work_with_markup = {
        "id": "https://openalex.org/W999999",
        "doi": "https://doi.org/10.1000/182",
        "title": "Study [RCT] on [CO2] reduction [/B]",
        "publication_year": 2024,
        "type": "article",
        "cited_by_count": 10,
        "abstract_inverted_index": {
            "Results": [0],
            "[95%": [1],
            "CI]": [2],
            "show": [3],
            "benefit": [4],
            "[/B]": [5],
        },
    }
    respx.get("https://api.openalex.org/works/W999999").mock(
        return_value=Response(200, json=work_with_markup)
    )

    result = runner.invoke(app, ["openalex", "get", "W999999"])

    assert result.exit_code == 0
    assert "Study [RCT] on [CO2] reduction [/B]" in result.stdout
    assert "[95% CI]" in result.stdout
    assert "[/B]" in result.stdout
