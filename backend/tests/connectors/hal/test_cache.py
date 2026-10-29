"""Tests unitaires du cache HTTP persistant pour HAL."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from csc.connectors.hal.cache import HalHttpCache


def test_normalize_url_deterministic_and_sorted() -> None:
    cache = HalHttpCache()
    url = "https://api.archives-ouvertes.fr/search/"
    params1 = [
        ("wt", "json"),
        ("q", '"taxe carbone"~3'),
        ("fq", "producedDateY_i:[2005 TO *]"),
        ("fq", "docType_s:(ART OR REPORT)"),
        ("fl", "halId_s,title_s"),
        ("rows", 10),
    ]
    params2 = [
        ("fl", "halId_s,title_s"),
        ("fq", "docType_s:(ART OR REPORT)"),
        ("rows", 10),
        ("q", '"taxe carbone"~3'),
        ("wt", "json"),
        ("fq", "producedDateY_i:[2005 TO *]"),
    ]

    norm1 = cache.normalize_url(url, params1)
    norm2 = cache.normalize_url(url, params2)
    assert norm1 == norm2
    assert "https://api.archives-ouvertes.fr/search" in norm1


def test_cache_miss_and_hit(tmp_path: Path) -> None:
    cache = HalHttpCache(cache_dir=tmp_path / "cache", ttl_seconds=3600)
    url = "https://api.archives-ouvertes.fr/search?q=carbone"

    assert cache.get(url) is None

    cache.set(
        normalized_url=url,
        status_code=200,
        headers={"content-type": "application/json"},
        data={"response": {"numFound": 1, "docs": [{"halId_s": "hal-01"}]}},
    )

    hit = cache.get(url)
    assert hit is not None
    assert hit.status_code == 200
    assert hit.data["response"]["numFound"] == 1


def test_cache_ttl_expiration(tmp_path: Path) -> None:
    cache = HalHttpCache(cache_dir=tmp_path / "cache", ttl_seconds=10)
    url = "https://api.archives-ouvertes.fr/search?q=test_expire"

    cache.set(
        normalized_url=url,
        status_code=200,
        headers={},
        data={"test": 123},
    )

    future = datetime.now(UTC) + timedelta(seconds=20)
    cached = cache.get(url)
    assert cached is not None
    assert cached.is_expired(current_time=future) is True


def test_cache_clear(tmp_path: Path) -> None:
    cache = HalHttpCache(cache_dir=tmp_path / "cache", ttl_seconds=3600)
    cache.set(
        normalized_url="https://api.archives-ouvertes.fr/search?q=1",
        status_code=200,
        headers={},
        data={},
    )
    cache.set(
        normalized_url="https://api.archives-ouvertes.fr/search?q=2",
        status_code=200,
        headers={},
        data={},
    )
    # Créer un fichier temporaire orphelin
    tmp_file = tmp_path / "cache" / "orphan.tmp"
    tmp_file.write_text("temporary")

    cleared = cache.clear()
    assert cleared == 2
    assert not tmp_file.exists()
    assert cache.clear() == 0
