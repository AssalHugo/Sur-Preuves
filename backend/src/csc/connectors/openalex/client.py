"""Client HTTP robuste pour l'API OpenAlex avec cache, rate-limiting et budget."""

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from csc.config import settings
from csc.connectors.openalex.budget import OpenAlexBudgetManager
from csc.connectors.openalex.cache import OpenAlexHttpCache
from csc.connectors.openalex.exceptions import (
    OpenAlexApiError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)
from csc.connectors.openalex.models import (
    Author,
    Institution,
    author_dict_to_author,
    institution_dict_to_institution,
    normalize_doi,
    normalize_openalex_id,
    work_dict_to_scholarly_work,
)
from csc.connectors.openalex.rate_limiter import OpenAlexRateLimiter
from csc.contracts.models import EvidenceQuery, ScholarlyWork
from csc.contracts.uuid_v7 import uuid7
from csc.db.models import EvidenceQueryModel

logger = logging.getLogger(__name__)


class OpenAlexClient:
    """Client OpenAlex avec gestion du budget gratuit, du cache 30j et des retries."""

    def __init__(
        self,
        api_key: str | None = None,
        email: str | None = None,
        base_url: str | None = None,
        cache: OpenAlexHttpCache | None = None,
        rate_limiter: OpenAlexRateLimiter | None = None,
        budget_manager: OpenAlexBudgetManager | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.openalex_api_key
        self.email = email if email is not None else settings.openalex_email
        self.base_url = (base_url or settings.openalex_base_url).rstrip("/")
        self.cache = cache or OpenAlexHttpCache()
        self.rate_limiter = rate_limiter or OpenAlexRateLimiter(has_api_key=bool(self.api_key))
        self.budget_manager = budget_manager or OpenAlexBudgetManager()
        self.transport = transport
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.recorded_queries: list[EvidenceQuery] = []

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.email:
            headers["User-Agent"] = f"csc-civic-tech/0.1.0 (mailto:{self.email})"
        else:
            headers["User-Agent"] = "csc-civic-tech/0.1.0"
        return headers

    def _format_filters(self, filters: dict[str, Any] | None) -> str | None:
        """Formate un dictionnaire en chaîne de filtres OpenAlex 'k1:v1,k2:v2'."""
        if not filters:
            return None
        parts: list[str] = []
        for k, v in filters.items():
            if v is None:
                continue
            if isinstance(v, bool):
                parts.append(f"{k}:{str(v).lower()}")
            elif isinstance(v, (list, tuple)):
                # Dans OpenAlex, les filtres OU sont séparés par un pipe |
                pipe_joined = "|".join(str(item) for item in v)
                parts.append(f"{k}:{pipe_joined}")
            else:
                parts.append(f"{k}:{v}")
        return ",".join(parts) if parts else None

    def _record_evidence_query(
        self,
        exact_query: str,
        parameters: dict[str, Any],
        results_count: int,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> EvidenceQuery:
        """Enregistre une EvidenceQuery en mémoire et optionnellement en base."""
        query_id = uuid7()
        effective_claim_id = claim_id or uuid7()

        record = EvidenceQuery(
            id=query_id,
            claim_id=effective_claim_id,
            source="openalex",
            exact_query=exact_query,
            parameters=parameters,
            queried_at=datetime.now(UTC),
            results_count=results_count,
        )
        self.recorded_queries.append(record)

        if session is not None and claim_id is not None:
            try:
                db_record = EvidenceQueryModel(
                    id=record.id,
                    claim_id=claim_id,
                    source=record.source,
                    exact_query=record.exact_query,
                    parameters=record.parameters,
                    queried_at=record.queried_at,
                    results_count=record.results_count,
                )
                session.add(db_record)
                session.flush()
            except Exception as exc:
                logger.warning("Échec d'enregistrement d'EvidenceQuery en base : %s", exc)

        return record

    def _execute_get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        is_semantic: bool = False,
        exact_query_desc: str = "",
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Exécute une requête GET avec cache HTTP, token bucket, budget et retries exponentiels."""
        clean_path = path.lstrip("/")
        full_url = f"{self.base_url}/{clean_path}"
        req_params = dict(params or {})

        normalized_url = self.cache.normalize_url(full_url, req_params)

        # 1. Vérification du cache persistant (TTL 30j)
        cached_resp = self.cache.get(normalized_url)
        if cached_resp is not None:
            data = cached_resp.data
            if isinstance(data, dict):
                count = len(data["results"]) if "results" in data else (1 if "id" in data else 0)
            else:
                count = 1
            self._record_evidence_query(
                exact_query=exact_query_desc or normalized_url,
                parameters={
                    "url": normalized_url,
                    "params": req_params,
                    "credits_used": 0.0,
                    "cached": True,
                },
                results_count=count,
                claim_id=claim_id,
                session=session,
            )
            return data  # type: ignore[no-any-return]

        # 2. Vérification préventive du budget quotidien (90%)
        self.budget_manager.check_budget_before_call()

        # 3. Limiteur de débit (Token Bucket)
        self.rate_limiter.acquire(is_semantic=is_semantic, wait=True)

        # 4. Préparation de la requête réelle avec clé API si présente
        call_params = dict(req_params)
        if self.api_key and "api_key" not in call_params:
            call_params["api_key"] = self.api_key

        headers = self._build_headers()

        # 5. Boucle d'exécution avec retries exponentiels
        last_exception: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(
                    transport=self.transport,
                    timeout=self.timeout,
                ) as client:
                    resp = client.get(full_url, params=call_params, headers=headers)

                # Gestion des statuts
                if resp.status_code == 200:
                    data = resp.json()

                    # Extraction des crédits consommés
                    credits_str = resp.headers.get("x-ratelimit-credits-used", "1.0")
                    try:
                        credits_used = float(credits_str)
                    except ValueError:
                        credits_used = 1.0

                    remaining_str = resp.headers.get("x-ratelimit-remaining")
                    remaining = float(remaining_str) if remaining_str else None

                    limit_str = resp.headers.get("x-ratelimit-limit")
                    limit = float(limit_str) if limit_str else None

                    # Enregistrement dans le gestionnaire de budget
                    self.budget_manager.record_usage(
                        credits_used=credits_used,
                        remaining_reported=remaining,
                        limit_reported=limit,
                    )

                    # Enregistrement dans le cache HTTP
                    self.cache.set(
                        normalized_url=normalized_url,
                        status_code=200,
                        headers=dict(resp.headers),
                        data=data,
                        credits_used=credits_used,
                    )

                    # Traçabilité EvidenceQuery
                    if isinstance(data, dict):
                        count = (
                            len(data["results"])
                            if "results" in data
                            else (1 if "id" in data else 0)
                        )
                    else:
                        count = 1
                    self._record_evidence_query(
                        exact_query=exact_query_desc or normalized_url,
                        parameters={
                            "url": normalized_url,
                            "params": req_params,
                            "credits_used": credits_used,
                            "cached": False,
                        },
                        results_count=count,
                        claim_id=claim_id,
                        session=session,
                    )

                    return data  # type: ignore[no-any-return]

                if resp.status_code == 404:
                    raise OpenAlexNotFoundError(
                        f"Ressource introuvable chez OpenAlex ({full_url}) : HTTP 404"
                    )

                if resp.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = resp.headers.get("retry-after")
                        wait_seconds = (
                            float(retry_after)
                            if retry_after
                            else self.backoff_factor * (2**attempt)
                        )
                        time.sleep(min(wait_seconds, 10.0))
                        continue
                    raise OpenAlexRateLimitError(
                        f"Débit OpenAlex dépassé (HTTP 429) après {self.max_retries} tentatives."
                    )

                if resp.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(self.backoff_factor * (2**attempt))
                        continue
                    raise OpenAlexApiError(
                        f"Erreur serveur OpenAlex (HTTP {resp.status_code}) "
                        f"après {self.max_retries} retries."
                    )

                # Autres codes HTTP (4xx non gérés)
                raise OpenAlexApiError(
                    f"Erreur requête OpenAlex (HTTP {resp.status_code}) : {resp.text}"
                )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor * (2**attempt))
                    continue
                raise OpenAlexApiError(
                    f"Erreur de communication réseau avec OpenAlex : {exc}"
                ) from exc

        if last_exception:
            raise OpenAlexApiError(
                f"Impossible de joindre OpenAlex : {last_exception}"
            ) from last_exception
        raise OpenAlexApiError(f"Échec d'appel OpenAlex vers {full_url}")

    def search_works(
        self,
        query: str = "",
        *,
        filters: dict[str, Any] | None = None,
        sort: str = "cited_by_count:desc",
        per_page: int = 50,
        max_results: int = 200,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[ScholarlyWork]:
        """Recherche des travaux scientifiques avec filtres, tri et pagination curseur."""
        all_works: list[ScholarlyWork] = []
        page_size = max(1, min(per_page, 100))
        cursor: str | None = "*"

        filter_str = self._format_filters(filters)

        while cursor and len(all_works) < max_results:
            params: dict[str, Any] = {
                "per_page": page_size,
                "sort": sort,
                "cursor": cursor,
            }
            if query.strip():
                params["search"] = query.strip()
            if filter_str:
                params["filter"] = filter_str

            desc = f"search_works: query='{query}', filters='{filter_str}', cursor='{cursor}'"
            payload = self._execute_get(
                "works",
                params=params,
                exact_query_desc=desc,
                claim_id=claim_id,
                session=session,
            )

            results = payload.get("results") or []
            if not results:
                break

            for item in results:
                all_works.append(work_dict_to_scholarly_work(item))
                if len(all_works) >= max_results:
                    break

            meta = payload.get("meta") or {}
            next_cursor = meta.get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        return all_works[:max_results]

    def semantic_search_works(
        self,
        text: str,
        *,
        filters: dict[str, Any] | None = None,
        k: int = 50,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[ScholarlyWork]:
        """Recherche sémantique par similarité conceptuelle (débit restreint à 1 req/s)."""
        per_page = max(1, min(k, 100))
        filter_str = self._format_filters(filters)

        params: dict[str, Any] = {
            "search": text.strip(),
            "per_page": per_page,
        }
        if filter_str:
            params["filter"] = filter_str

        desc = f"semantic_search: text='{text[:60]}...', filters='{filter_str}'"
        payload = self._execute_get(
            "works",
            params=params,
            is_semantic=True,
            exact_query_desc=desc,
            claim_id=claim_id,
            session=session,
        )

        results = payload.get("results") or []
        works = [work_dict_to_scholarly_work(item) for item in results]
        return works[:k]

    def get_work(
        self,
        id_or_doi: str,
        *,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> ScholarlyWork:
        """Récupère une publication spécifique à partir de son DOI ou de son ID OpenAlex."""
        clean_target = id_or_doi.strip()
        is_doi = (
            clean_target.startswith("10.")
            or "doi.org" in clean_target
            or clean_target.startswith("doi:")
        )
        if is_doi:
            doi = normalize_doi(clean_target)
            if not doi:
                raise ValueError(f"DOI invalide : {id_or_doi}")
            path = f"works/https://doi.org/{doi}"
        else:
            openalex_id = normalize_openalex_id(clean_target)
            if not openalex_id:
                raise ValueError(f"Identifiant OpenAlex invalide : {id_or_doi}")
            path = f"works/{openalex_id}"

        desc = f"get_work: id_or_doi='{id_or_doi}'"
        payload = self._execute_get(
            path,
            exact_query_desc=desc,
            claim_id=claim_id,
            session=session,
        )
        return work_dict_to_scholarly_work(payload)

    def find_systematic_reviews(
        self,
        topic_query: str,
        *,
        since_year: int = 2005,
        sort: str = "cited_by_count:desc",
        per_page: int = 50,
        max_results: int = 100,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[ScholarlyWork]:
        """Recherche spécifiquement les revues systématiques et méta-analyses sur un sujet."""
        filters = {
            "type": "review",
            "from_publication_date": f"{since_year}-01-01",
        }
        works = self.search_works(
            query=topic_query,
            filters=filters,
            sort=sort,
            per_page=per_page,
            max_results=max_results,
            claim_id=claim_id,
            session=session,
        )
        # S'assure que le drapeau is_systematic_review est bien activé
        for w in works:
            w.is_systematic_review = True
        return works

    def top_institutions(
        self,
        topic_id: str,
        n: int = 3,
        *,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[Institution]:
        """Récupère les institutions de recherche les plus citées pour un sujet donné."""
        clean_topic = normalize_openalex_id(topic_id) or topic_id.strip()
        params: dict[str, Any] = {
            "filter": f"topics.id:{clean_topic}",
            "sort": "cited_by_count:desc",
            "per_page": max(1, min(n, 50)),
        }
        desc = f"top_institutions: topic_id='{clean_topic}', n={n}"
        payload = self._execute_get(
            "institutions",
            params=params,
            exact_query_desc=desc,
            claim_id=claim_id,
            session=session,
        )
        results = payload.get("results") or []
        institutions = [institution_dict_to_institution(item) for item in results]
        return institutions[:n]

    def top_authors(
        self,
        topic_id: str,
        n: int = 20,
        *,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[Author]:
        """Récupère les auteurs de référence pour un sujet donné (recherche de relecteurs)."""
        clean_topic = normalize_openalex_id(topic_id) or topic_id.strip()
        params: dict[str, Any] = {
            "filter": f"topics.id:{clean_topic}",
            "sort": "cited_by_count:desc",
            "per_page": max(1, min(n, 100)),
        }
        desc = f"top_authors: topic_id='{clean_topic}', n={n}"
        payload = self._execute_get(
            "authors",
            params=params,
            exact_query_desc=desc,
            claim_id=claim_id,
            session=session,
        )
        results = payload.get("results") or []
        authors = [author_dict_to_author(item) for item in results]
        return authors[:n]
