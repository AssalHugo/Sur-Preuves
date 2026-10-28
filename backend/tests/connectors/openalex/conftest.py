"""Fixtures partagées pour les tests du connecteur OpenAlex."""

import json
from pathlib import Path
from typing import Any

import pytest

from csc.connectors.openalex.budget import OpenAlexBudgetManager
from csc.connectors.openalex.cache import OpenAlexHttpCache

CASSETTES_DIR = Path(__file__).resolve().parent / "cassettes"


@pytest.fixture
def load_cassette() -> Any:
    """Charge une cassette JSON enregistrée."""

    def _loader(name: str) -> dict[str, Any]:
        path = CASSETTES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Cassette {name}.json introuvable dans {CASSETTES_DIR}")
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    return _loader


@pytest.fixture
def tmp_openalex_cache(tmp_path: Path) -> OpenAlexHttpCache:
    """Fournit une instance de cache HTTP isolée sur un répertoire temporaire."""
    return OpenAlexHttpCache(cache_dir=tmp_path / "cache", ttl_seconds=3600)


@pytest.fixture
def tmp_budget_manager(tmp_path: Path) -> OpenAlexBudgetManager:
    """Fournit un gestionnaire de budget isolé sur un répertoire temporaire."""
    return OpenAlexBudgetManager(
        ledger_dir=tmp_path / "budget",
        daily_limit=1000.0,
        threshold_pct=0.90,
    )
