"""Tests unitaires pour le limiteur de débit Token Bucket OpenAlex."""

from csc.connectors.openalex.rate_limiter import OpenAlexRateLimiter, TokenBucket


def test_token_bucket_acquire_and_exhaustion() -> None:
    current_time = 1000.0

    def mock_time() -> float:
        return current_time

    bucket = TokenBucket(rate=2.0, capacity=2.0, time_func=mock_time)

    # 1er et 2e jeton disponibles immédiatement
    assert bucket.acquire(tokens=1.0, wait=False) is True
    assert bucket.acquire(tokens=1.0, wait=False) is True

    # 3e jeton : plus de jetons disponibles sans attente
    assert bucket.acquire(tokens=1.0, wait=False) is False

    # Avance de 0.5s : 0.5s * 2.0 = 1 jeton rechargé
    current_time += 0.5
    assert bucket.acquire(tokens=1.0, wait=False) is True
    assert bucket.acquire(tokens=1.0, wait=False) is False


def test_token_bucket_capacity_clamping() -> None:
    current_time = 1000.0

    def mock_time() -> float:
        return current_time

    bucket = TokenBucket(rate=5.0, capacity=5.0, time_func=mock_time)

    # Avance de 10 secondes : ne doit pas dépasser la capacité de 5
    current_time += 10.0
    for _ in range(5):
        assert bucket.acquire(tokens=1.0, wait=False) is True
    assert bucket.acquire(tokens=1.0, wait=False) is False


def test_openalex_rate_limiter_semantic_and_general() -> None:
    current_time = 1000.0

    def mock_time() -> float:
        return current_time

    limiter = OpenAlexRateLimiter(
        has_api_key=False,
        general_rate=10.0,
        semantic_rate=1.0,
        time_func=mock_time,
    )

    # Recherche sémantique consomme sur les deux seaux
    assert limiter.acquire(is_semantic=True, wait=False) is True
    # Deuxième appel sémantique immédiat échoue car semantic_rate = 1.0 req/s
    assert limiter.acquire(is_semantic=True, wait=False) is False

    # Mais un appel général standard reste possible car general_rate = 10.0
    assert limiter.acquire(is_semantic=False, wait=False) is True
