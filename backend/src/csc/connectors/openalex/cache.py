"""Cache HTTP persistant sur disque avec clé d'URL normalisée et TTL de 30 jours."""

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field

from csc.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 jours


class CachedApiResponse(BaseModel):
    """Représentation d'une réponse HTTP OpenAlex mise en cache."""

    normalized_url: str
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    data: Any
    cached_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    credits_used: float = 0.0

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Vérifie si l'entrée a dépassé sa durée de vie (TTL)."""
        now = current_time or datetime.now(UTC)
        expiration = self.cached_at + timedelta(seconds=self.ttl_seconds)
        return now > expiration


class OpenAlexHttpCache:
    """Gestionnaire de cache persistant sur disque pour les requêtes HTTP OpenAlex."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.cache_dir = cache_dir or settings.openalex_cache_dir
        self.ttl_seconds = ttl_seconds

    def _resolve_dir(self) -> Path:
        target = self.cache_dir
        if not target.is_absolute():
            # Racine du dépôt
            root = Path(__file__).resolve().parents[4]
            target = root / target
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def normalize_url(url: str, params: dict[str, Any] | None = None) -> str:
        """Normalise une URL et ses paramètres pour produire une clé de cache reproductible.

        - Supprime la clé API pour ne pas fragmenter le cache et ne pas persister de secret.
        - Trie les paramètres de requête alphabétiquement.
        - Minusculise le protocole et le nom d'hôte.
        """
        split = urlsplit(url)
        query_items = parse_qsl(split.query, keep_blank_values=True)

        if params:
            for k, v in params.items():
                if v is None:
                    continue
                if isinstance(v, (list, tuple)):
                    for item in v:
                        query_items.append((k, str(item)))
                elif isinstance(v, bool):
                    query_items.append((k, str(v).lower()))
                else:
                    query_items.append((k, str(v)))

        # Filtrage des clés sensibles (clé API)
        filtered_items = [(k, v) for k, v in query_items if k.lower() != "api_key"]

        # Tri déterministe
        filtered_items.sort(key=lambda pair: (pair[0], pair[1]))
        normalized_query = urlencode(filtered_items)

        normalized = urlunsplit(
            (
                split.scheme.lower(),
                split.netloc.lower(),
                split.path,
                normalized_query,
                "",  # fragment ignoré
            )
        )
        return normalized

    def compute_key(self, normalized_url: str) -> str:
        """Calcule le hash SHA-256 de l'URL normalisée."""
        return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()

    def get(self, normalized_url: str) -> CachedApiResponse | None:
        """Récupère une réponse en cache si disponible et non expirée."""
        key = self.compute_key(normalized_url)
        path = self._resolve_dir() / f"{key}.json"
        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            cached = CachedApiResponse.model_validate(data)
            if cached.is_expired():
                try:
                    path.unlink()
                except OSError:
                    pass
                return None
            return cached
        except Exception as exc:
            logger.debug("Erreur lors de la lecture du cache pour %s: %s", normalized_url, exc)
            return None

    def set(
        self,
        normalized_url: str,
        status_code: int,
        headers: dict[str, str],
        data: Any,
        credits_used: float = 0.0,
    ) -> None:
        """Enregistre une réponse HTTP dans le cache disque."""
        key = self.compute_key(normalized_url)
        path = self._resolve_dir() / f"{key}.json"

        # Filtrage des headers pour ne garder que l'essentiel
        safe_headers = {
            k.lower(): v
            for k, v in headers.items()
            if k.lower()
            in (
                "content-type",
                "x-ratelimit-limit",
                "x-ratelimit-remaining",
                "x-ratelimit-credits-used",
                "x-ratelimit-reset",
            )
        }

        cached = CachedApiResponse(
            normalized_url=normalized_url,
            status_code=status_code,
            headers=safe_headers,
            data=data,
            cached_at=datetime.now(UTC),
            ttl_seconds=self.ttl_seconds,
            credits_used=credits_used,
        )

        try:
            path.write_text(cached.model_dump_json(indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Impossible d'écrire l'entrée de cache OpenAlex : %s", exc)

    def clear(self) -> None:
        """Vide l'intégralité du cache disque."""
        target_dir = self._resolve_dir()
        for f in target_dir.glob("*.json"):
            try:
                f.unlink()
            except OSError:
                pass
