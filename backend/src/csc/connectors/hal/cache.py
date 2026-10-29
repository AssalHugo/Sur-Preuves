"""Cache HTTP persistant sur disque pour les requêtes HAL Solr (TTL 30 jours)."""

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, Field

from csc.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 30 * 24 * 3600  # 30 jours


class CachedHalApiResponse(BaseModel):
    """Représentation d'une réponse API HAL Solr stockée en cache."""

    normalized_url: str
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    data: Any
    cached_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl_seconds: int = DEFAULT_TTL_SECONDS

    def is_expired(self, current_time: datetime | None = None) -> bool:
        """Vérifie si la réponse a expiré selon son TTL."""
        now = current_time or datetime.now(UTC)
        expiration = self.cached_at + timedelta(seconds=self.ttl_seconds)
        return now > expiration


class HalHttpCache:
    """Gestionnaire de cache sur disque pour l'API HAL Solr."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.cache_dir = cache_dir or settings.hal_cache_dir
        self.ttl_seconds = ttl_seconds

    def _resolve_dir(self) -> Path:
        target = self.cache_dir
        if not target.is_absolute():
            from csc.config import _PROJECT_ROOT

            target = _PROJECT_ROOT / target
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def normalize_url(
        url: str, params: dict[str, Any] | list[tuple[str, Any]] | None = None
    ) -> str:
        """Normalise une URL et ses paramètres pour un hachage déterministe."""
        split = urlsplit(url)
        query_items: list[tuple[str, str]] = list(parse_qsl(split.query, keep_blank_values=True))

        if params:
            items_list: list[tuple[str, Any]]
            if isinstance(params, dict):
                items_list = list(params.items())
            else:
                items_list = list(params)

            for k, v in items_list:
                if v is None:
                    continue
                if isinstance(v, (list, tuple)):
                    for item in v:
                        query_items.append((k, str(item)))
                elif isinstance(v, bool):
                    query_items.append((k, str(v).lower()))
                else:
                    query_items.append((k, str(v)))

        # Tri déterministe sur (clé, valeur)
        query_items.sort(key=lambda pair: (pair[0], pair[1]))
        normalized_query = urlencode(query_items)

        normalized = urlunsplit(
            (
                split.scheme.lower(),
                split.netloc.lower(),
                split.path.rstrip("/"),
                normalized_query,
                "",  # fragment ignoré
            )
        )
        return normalized

    def compute_key(self, normalized_url: str) -> str:
        """Calcule la clé SHA-256 de l'URL normalisée."""
        return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()

    def get(self, normalized_url: str) -> CachedHalApiResponse | None:
        """Récupère une réponse valide depuis le cache si elle existe et n'a pas expiré."""
        key = self.compute_key(normalized_url)
        cache_file = self._resolve_dir() / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            content = cache_file.read_text(encoding="utf-8")
            cached = CachedHalApiResponse.model_validate_json(content)
            if cached.is_expired():
                logger.debug("Entrée de cache HAL expirée pour %s", normalized_url)
                try:
                    cache_file.unlink(missing_ok=True)
                except OSError:
                    pass
                return None
            return cached
        except Exception as exc:
            logger.warning("Échec de lecture du cache HAL (%s) : %s", cache_file, exc)
            return None

    def set(
        self,
        normalized_url: str,
        status_code: int,
        headers: dict[str, str],
        data: Any,
    ) -> Path:
        """Enregistre une réponse dans le cache de manière atomique."""
        key = self.compute_key(normalized_url)
        cache_dir = self._resolve_dir()
        target_file = cache_dir / f"{key}.json"
        tmp_file = cache_dir / f"{key}.tmp"

        record = CachedHalApiResponse(
            normalized_url=normalized_url,
            status_code=status_code,
            headers=headers,
            data=data,
            cached_at=datetime.now(UTC),
            ttl_seconds=self.ttl_seconds,
        )

        tmp_file.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        tmp_file.replace(target_file)
        return target_file

    def clear(self) -> int:
        """Vide l'ensemble des fichiers du cache HAL."""
        count = 0
        cache_dir = self._resolve_dir()
        if cache_dir.exists():
            for pattern in ("*.json", "*.tmp"):
                for item in cache_dir.glob(pattern):
                    try:
                        item.unlink()
                        if pattern == "*.json":
                            count += 1
                    except OSError:
                        pass
        return count
