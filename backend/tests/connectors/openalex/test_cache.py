"""Tests unitaires pour le cache HTTP persistant OpenAlex."""

from datetime import UTC, datetime, timedelta
from typing import Any

from csc.connectors.openalex.cache import CachedApiResponse, OpenAlexHttpCache


def test_normalize_url_deterministic_and_strips_api_key(
    tmp_openalex_cache: OpenAlexHttpCache,
) -> None:
    url = "https://API.OpenAlex.org/works?b=2&api_key=SECRET_KEY&a=1"
    normalized = tmp_openalex_cache.normalize_url(url)
    assert normalized == "https://api.openalex.org/works?a=1&b=2"
    assert "SECRET_KEY" not in normalized
    assert "api_key" not in normalized


def test_normalize_url_with_dict_params(tmp_openalex_cache: OpenAlexHttpCache) -> None:
    url = "https://api.openalex.org/works"
    params = {
        "search": "carbon tax",
        "filter": "type:review",
        "api_key": "SUPER_SECRET",
        "is_oa": True,
    }
    normalized = tmp_openalex_cache.normalize_url(url, params=params)
    assert "SUPER_SECRET" not in normalized
    assert (
        normalized
        == "https://api.openalex.org/works?filter=type%3Areview&is_oa=true&search=carbon+tax"
    )


def test_cache_miss_and_set_get(tmp_openalex_cache: OpenAlexHttpCache) -> None:
    url = "https://api.openalex.org/works?search=test"
    assert tmp_openalex_cache.get(url) is None

    sample_data = {"results": [{"id": "W123", "title": "Test"}]}
    tmp_openalex_cache.set(
        normalized_url=url,
        status_code=200,
        headers={"content-type": "application/json", "x-ratelimit-credits-used": "1.0"},
        data=sample_data,
        credits_used=1.0,
    )

    cached = tmp_openalex_cache.get(url)
    assert cached is not None
    assert cached.status_code == 200
    assert cached.data == sample_data
    assert cached.credits_used == 1.0


def test_cache_ttl_expiration(tmp_openalex_cache: OpenAlexHttpCache) -> None:
    url = "https://api.openalex.org/works?search=expired"
    sample_data: dict[str, Any] = {"results": []}

    tmp_openalex_cache.set(
        normalized_url=url,
        status_code=200,
        headers={},
        data=sample_data,
    )

    cached = tmp_openalex_cache.get(url)
    assert cached is not None
    assert not cached.is_expired()

    # Simulation d'une expiration (31 jours plus tard)
    future_time = datetime.now(UTC) + timedelta(days=31)
    assert cached.is_expired(current_time=future_time)

    # Modifier artificiellement la date de mise en cache pour tester get()
    key = tmp_openalex_cache.compute_key(url)
    path = tmp_openalex_cache._resolve_dir() / f"{key}.json"
    expired_entry = CachedApiResponse(
        normalized_url=url,
        status_code=200,
        headers={},
        data=sample_data,
        cached_at=datetime.now(UTC) - timedelta(days=31),
        ttl_seconds=30 * 86400,
    )
    path.write_text(expired_entry.model_dump_json(), encoding="utf-8")

    assert tmp_openalex_cache.get(url) is None
    assert not path.exists(), "Le fichier de cache expiré doit être nettoyé"


def test_cache_clear(tmp_openalex_cache: OpenAlexHttpCache) -> None:
    tmp_openalex_cache.set("https://api.openalex.org/w1", 200, {}, {"id": 1})
    tmp_openalex_cache.set("https://api.openalex.org/w2", 200, {}, {"id": 2})

    cache_dir = tmp_openalex_cache._resolve_dir()
    assert len(list(cache_dir.glob("*.json"))) == 2

    tmp_openalex_cache.clear()
    assert len(list(cache_dir.glob("*.json"))) == 0
