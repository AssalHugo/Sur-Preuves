"""Fixtures partagées pour les tests du connecteur HAL."""

import json
from pathlib import Path
from typing import Any

import pytest

from csc.connectors.hal.cache import HalHttpCache
from csc.connectors.hal.client import HalClient

CASSETTES_DIR = Path(__file__).resolve().parent / "cassettes"


@pytest.fixture
def load_hal_cassette() -> Any:
    """Charge une cassette JSON enregistrée pour HAL."""

    def _loader(name: str) -> dict[str, Any]:
        path = CASSETTES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Cassette HAL {name}.json introuvable dans {CASSETTES_DIR}")
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    return _loader


@pytest.fixture
def tmp_hal_cache(tmp_path: Path) -> HalHttpCache:
    """Fournit un cache HTTP isolé dans un répertoire temporaire."""
    return HalHttpCache(cache_dir=tmp_path / "hal_cache", ttl_seconds=3600)


@pytest.fixture
def mock_hal_client(tmp_hal_cache: HalHttpCache) -> HalClient:
    """Fournit une instance HalClient configurée pour les tests avec backoff rapide."""
    return HalClient(
        base_url="https://api.archives-ouvertes.fr/search",
        cache=tmp_hal_cache,
        timeout=5.0,
        max_retries=2,
        backoff_factor=0.01,
    )
