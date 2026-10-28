"""Limiteur de débit par seau à jetons (Token Bucket) pour l'API OpenAlex."""

import threading
import time
from collections.abc import Callable


class TokenBucket:
    """Implémentation thread-safe de l'algorithme Token Bucket."""

    def __init__(
        self,
        rate: float,
        capacity: float | None = None,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        """Initialise le seau à jetons.

        Args:
            rate: Nombre de jetons ajoutés par seconde.
            capacity: Capacité maximale du seau (par défaut égale à rate).
            time_func: Fonction fournissant le temps courant (par défaut time.monotonic).
        """
        self.rate = rate
        self.capacity = capacity if capacity is not None else rate
        self.tokens = self.capacity
        self._time_func = time_func or time.monotonic
        self.last_update = self._time_func()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0, wait: bool = True) -> bool:
        """Consomme un nombre donné de jetons, avec attente optionnelle."""
        with self._lock:
            now = self._time_func()
            elapsed = max(0.0, now - self.last_update)
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not wait:
                return False

            needed = tokens - self.tokens
            sleep_time = needed / self.rate

        if sleep_time > 0:
            time.sleep(sleep_time)
            with self._lock:
                now = self._time_func()
                elapsed = max(0.0, now - self.last_update)
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.tokens = max(0.0, self.tokens - tokens)

        return True


class OpenAlexRateLimiter:
    """Coordinateur de débit pour l'API OpenAlex.

    Gère distinctement le débit des requêtes générales (10 req/s sans clé, 30 req/s avec clé)
    et le débit restreint de la recherche sémantique (1 req/s maximum).
    """

    def __init__(
        self,
        has_api_key: bool = False,
        general_rate: float | None = None,
        semantic_rate: float = 1.0,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        if general_rate is None:
            general_rate = 30.0 if has_api_key else 10.0

        self.general_limiter = TokenBucket(rate=general_rate, time_func=time_func)
        self.semantic_limiter = TokenBucket(rate=semantic_rate, time_func=time_func)

    def acquire(self, is_semantic: bool = False, wait: bool = True) -> bool:
        """Acquiert l'autorisation d'émettre une requête."""
        if is_semantic:
            acquired_semantic = self.semantic_limiter.acquire(tokens=1.0, wait=wait)
            if not acquired_semantic:
                return False
        return self.general_limiter.acquire(tokens=1.0, wait=wait)
