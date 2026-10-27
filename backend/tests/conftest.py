"""Configuration globale des fixtures pytest."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """Fixture retournant un CliRunner Typer."""
    return CliRunner()
