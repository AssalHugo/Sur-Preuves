"""Client HTTP pour l'API Solr de l'archive ouverte HAL (CCSD/CNRS)."""

import logging
import re
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from csc.config import settings
from csc.connectors.hal.cache import HalHttpCache
from csc.connectors.hal.exceptions import (
    HalApiError,
    HalNotFoundError,
    HalRateLimitError,
)
from csc.connectors.hal.models import (
    build_proximity_query,
    normalize_hal_id,
    parse_hal_doc,
)
from csc.contracts.models import EvidenceQuery, ScholarlyWork
from csc.contracts.uuid_v7 import uuid7
from csc.db.models import EvidenceQueryModel

logger = logging.getLogger(__name__)

DEFAULT_FL_FIELDS = (
    "halId_s,doiId_s,title_s,abstract_s,authFullName_s,structName_s,"
    "producedDateY_i,docType_s,journalTitle_s,uri_s,fileMain_s"
)


class HalClient:
    """Client officiel pour interroger l'API Solr de HAL sans authentification."""

    def __init__(
        self,
        base_url: str | None = None,
        cache: HalHttpCache | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.base_url = (base_url or settings.hal_base_url).rstrip("/")
        self.cache = cache or HalHttpCache()
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.recorded_queries: list[EvidenceQuery] = []
        self._http_client = httpx.Client(
            timeout=self.timeout,
            headers={
                "User-Agent": "ComparateurScience2027/1.0 (+https://github.com/AssalHugo/civic-tech)",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        """Ferme la session HTTP sous-jacente."""
        self._http_client.close()

    def clear_recorded_queries(self) -> None:
        """Vide l'historique en mémoire des requêtes de traçabilité."""
        self.recorded_queries.clear()

    def __enter__(self) -> "HalClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _record_evidence_query(
        self,
        exact_query: str,
        parameters: dict[str, Any],
        results_count: int,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> EvidenceQuery:
        """Enregistre une EvidenceQuery en mémoire et optionnellement dans la base de données."""
        query_id = uuid7()
        effective_claim_id = claim_id or uuid7()

        record = EvidenceQuery(
            id=query_id,
            claim_id=effective_claim_id,
            source="hal",
            exact_query=exact_query,
            parameters=parameters,
            queried_at=datetime.now(UTC),
            results_count=results_count,
        )
        if len(self.recorded_queries) >= 1000:
            self.recorded_queries.pop(0)
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
        params: list[tuple[str, Any]],
        *,
        exact_query_desc: str = "",
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Exécute une requête GET vers l'API Solr avec cache persistant et retries exponentiels."""
        normalized_url = self.cache.normalize_url(self.base_url, params)

        # 1. Vérification du cache disque
        cached_resp = self.cache.get(normalized_url)
        if cached_resp is not None:
            data = cached_resp.data
            count = 0
            num_found: int | None = None
            if isinstance(data, dict):
                resp_obj = data.get("response")
                if isinstance(resp_obj, dict):
                    docs = resp_obj.get("docs")
                    count = len(docs) if isinstance(docs, list) else 0
                    raw_num_found = resp_obj.get("numFound")
                    if isinstance(raw_num_found, int):
                        num_found = raw_num_found

            self._record_evidence_query(
                exact_query=exact_query_desc or normalized_url,
                parameters={
                    "url": normalized_url,
                    "params": params,
                    "cached": True,
                    "num_found": num_found,
                },
                results_count=count,
                claim_id=claim_id,
                session=session,
            )
            return data if isinstance(data, dict) else {}

        # 2. Exécution réseau avec retries
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http_client.get(self.base_url, params=params)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception as json_err:
                        raise HalApiError(
                            f"Réponse JSON invalide de HAL : {json_err}"
                        ) from json_err

                    count = 0
                    num_found = None
                    if isinstance(data, dict):
                        resp_obj = data.get("response")
                        if isinstance(resp_obj, dict):
                            docs = resp_obj.get("docs")
                            count = len(docs) if isinstance(docs, list) else 0
                            raw_num_found = resp_obj.get("numFound")
                            if isinstance(raw_num_found, int):
                                num_found = raw_num_found

                    # Mise en cache
                    self.cache.set(
                        normalized_url=normalized_url,
                        status_code=200,
                        headers=dict(resp.headers),
                        data=data,
                    )

                    # Enregistrement EvidenceQuery
                    self._record_evidence_query(
                        exact_query=exact_query_desc or normalized_url,
                        parameters={
                            "url": normalized_url,
                            "params": params,
                            "cached": False,
                            "num_found": num_found,
                        },
                        results_count=count,
                        claim_id=claim_id,
                        session=session,
                    )
                    return data if isinstance(data, dict) else {}

                if resp.status_code == 404:
                    raise HalNotFoundError(
                        f"Ressource introuvable chez HAL ({normalized_url}) : HTTP 404"
                    )

                if resp.status_code == 429:
                    if attempt < self.max_retries:
                        retry_after = resp.headers.get("retry-after")
                        wait_seconds = self.backoff_factor * (2**attempt)
                        if retry_after:
                            try:
                                wait_seconds = float(retry_after)
                            except (ValueError, TypeError):
                                pass
                        time.sleep(min(wait_seconds, 10.0))
                        continue
                    raise HalRateLimitError(
                        f"Débit HAL dépassé (HTTP 429) après {self.max_retries} tentatives."
                    )

                if resp.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(self.backoff_factor * (2**attempt))
                        continue
                    raise HalApiError(
                        f"Erreur serveur HAL (HTTP {resp.status_code}) "
                        f"après {self.max_retries} retries."
                    )

                raise HalApiError(
                    f"Erreur inattendue de l'API HAL HTTP {resp.status_code} : {resp.text}"
                )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor * (2**attempt))
                    continue
                raise HalApiError(
                    f"Échec réseau lors de la communication avec HAL ({normalized_url}) : {exc}"
                ) from exc

        raise HalApiError(f"Tentatives épuisées pour {normalized_url}")

    def search(
        self,
        query: str = "",
        *,
        doc_types: Sequence[str] = ("ART", "REPORT", "THESE", "COUV"),
        since_year: int = 2005,
        rows: int = 100,
        proximity: tuple[str, str, int] | None = None,
        struct_ids: Sequence[int] | None = None,
        sort: str | None = None,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[ScholarlyWork]:
        """Recherche des publications dans HAL selon divers filtres et critères de proximité."""
        # 1. Construction de la requête principale q
        clean_q = (query or "").strip()
        if proximity is not None:
            t1, t2, dist = proximity
            prox_clause = build_proximity_query(t1, t2, dist)
            normalized_terms = f"{t1.strip().lower()} {t2.strip().lower()}"
            if not clean_q or clean_q in ("*", "*:*"):
                solr_q = prox_clause
            elif re.sub(r"\s+", " ", clean_q.strip('"')).lower() == normalized_terms:
                solr_q = prox_clause
            else:
                solr_q = f"({clean_q}) AND {prox_clause}"
        else:
            solr_q = clean_q if clean_q and clean_q not in ("*", "") else "*:*"

        # 2. Construction des filtres fq
        fq_list: list[str] = []

        if doc_types:
            clean_types = [str(d).strip().upper() for d in doc_types if str(d).strip()]
            if clean_types:
                fq_list.append(f"docType_s:({' OR '.join(clean_types)})")

        if since_year is not None:
            fq_list.append(f"producedDateY_i:[{int(since_year)} TO *]")

        if struct_ids:
            clean_structs = [str(int(s)) for s in struct_ids]
            if clean_structs:
                fq_list.append(f"structId_i:({' OR '.join(clean_structs)})")

        # 3. Paramètres Solr
        params: list[tuple[str, Any]] = [
            ("q", solr_q),
            ("wt", "json"),
            ("fl", DEFAULT_FL_FIELDS),
            ("rows", max(1, int(rows))),
        ]
        for fq in fq_list:
            params.append(("fq", fq))

        if sort:
            params.append(("sort", sort))

        exact_desc = f"HAL search: q='{solr_q}', fq={fq_list}, rows={rows}"
        data = self._execute_get(
            params=params,
            exact_query_desc=exact_desc,
            claim_id=claim_id,
            session=session,
        )

        resp_obj = data.get("response")
        docs = resp_obj.get("docs") if isinstance(resp_obj, dict) else []
        if not isinstance(docs, list):
            return []

        works: list[ScholarlyWork] = []
        seen_hal_ids: set[str] = set()

        for doc in docs:
            if not isinstance(doc, dict):
                continue
            work = parse_hal_doc(doc)
            if work.hal_id and work.hal_id in seen_hal_ids:
                continue
            if work.hal_id:
                seen_hal_ids.add(work.hal_id)
            works.append(work)

        return works

    def search_by_structure(
        self,
        struct_ids: list[int],
        query: str = "*:*",
        *,
        doc_types: Sequence[str] = ("ART", "REPORT", "THESE", "COUV"),
        since_year: int = 2005,
        rows: int = 100,
        proximity: tuple[str, str, int] | None = None,
        sort: str | None = None,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> list[ScholarlyWork]:
        """Recherche des publications affiliées à une ou plusieurs structures de recherche."""
        return self.search(
            query=query,
            doc_types=doc_types,
            since_year=since_year,
            rows=rows,
            proximity=proximity,
            struct_ids=struct_ids,
            sort=sort,
            claim_id=claim_id,
            session=session,
        )

    def get(
        self,
        hal_id: str,
        *,
        claim_id: UUID | None = None,
        session: Session | None = None,
    ) -> ScholarlyWork:
        """Récupère une publication spécifique à partir de son identifiant HAL."""
        clean_id = normalize_hal_id(hal_id)
        if not clean_id:
            raise HalNotFoundError(f"Identifiant HAL invalide : {hal_id}")

        solr_q = f'halId_s:"{clean_id}"'
        params: list[tuple[str, Any]] = [
            ("q", solr_q),
            ("wt", "json"),
            ("fl", DEFAULT_FL_FIELDS),
            ("rows", 1),
        ]

        exact_desc = f"HAL get: {clean_id}"
        data = self._execute_get(
            params=params,
            exact_query_desc=exact_desc,
            claim_id=claim_id,
            session=session,
        )

        resp_obj = data.get("response")
        docs = resp_obj.get("docs") if isinstance(resp_obj, dict) else []
        if not isinstance(docs, list) or not docs:
            raise HalNotFoundError(f"Publication HAL introuvable ({clean_id})")

        first_doc = docs[0]
        if not isinstance(first_doc, dict):
            raise HalNotFoundError(f"Données invalides pour la publication HAL ({clean_id})")

        return parse_hal_doc(first_doc)
