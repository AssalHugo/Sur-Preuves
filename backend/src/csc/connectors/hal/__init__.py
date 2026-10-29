"""Connecteur HAL (archive ouverte nationale du CCSD / CNRS).

Ce module expose les fonctions de recherche documentaire Solr, de filtrage par structures
et de récupération unitaire de publications scientifiques françaises.
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from csc.connectors.hal.cache import HalHttpCache
from csc.connectors.hal.client import HalClient
from csc.connectors.hal.exceptions import (
    HalApiError,
    HalError,
    HalNotFoundError,
    HalRateLimitError,
)
from csc.connectors.hal.models import (
    KNOWN_STRUCTURES,
    ResearchStructure,
    build_proximity_query,
    escape_solr_phrase_term,
    normalize_doi,
    normalize_hal_id,
    parse_hal_doc,
    resolve_struct_id,
)
from csc.contracts.models import ScholarlyWork

_default_client: HalClient | None = None


def get_default_client() -> HalClient:
    """Retourne l'instance singleton par défaut du client HAL."""
    global _default_client
    if _default_client is None:
        _default_client = HalClient()
    return _default_client


def search(
    query: str = "",
    *,
    doc_types: Sequence[str] = ("ART", "REPORT", "THESE", "COUV"),
    since_year: int = 2005,
    rows: int = 100,
    proximity: tuple[str, str, int] | None = None,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[ScholarlyWork]:
    """Recherche des publications scientifiques dans l'archive ouverte HAL.

    Exemple de recherche de proximité :
        search("taxe carbone", proximity=("taxe", "carbone", 3))
    """
    return get_default_client().search(
        query=query,
        doc_types=doc_types,
        since_year=since_year,
        rows=rows,
        proximity=proximity,
        claim_id=claim_id,
        session=session,
    )


def search_by_structure(
    struct_ids: list[int],
    query: str = "*:*",
    *,
    doc_types: Sequence[str] = ("ART", "REPORT", "THESE", "COUV"),
    since_year: int = 2005,
    rows: int = 100,
    proximity: tuple[str, str, int] | None = None,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[ScholarlyWork]:
    """Recherche des travaux affiliés à des structures institutionnelles (INRAE, IPP, OFCE...)."""
    return get_default_client().search_by_structure(
        struct_ids=struct_ids,
        query=query,
        doc_types=doc_types,
        since_year=since_year,
        rows=rows,
        proximity=proximity,
        claim_id=claim_id,
        session=session,
    )


def get(
    hal_id: str,
    *,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> ScholarlyWork:
    """Récupère une publication spécifique à partir de son identifiant HAL."""
    return get_default_client().get(
        hal_id=hal_id,
        claim_id=claim_id,
        session=session,
    )


__all__ = [
    "KNOWN_STRUCTURES",
    "HalApiError",
    "HalClient",
    "HalError",
    "HalHttpCache",
    "HalNotFoundError",
    "HalRateLimitError",
    "ResearchStructure",
    "build_proximity_query",
    "escape_solr_phrase_term",
    "get",
    "get_default_client",
    "normalize_doi",
    "normalize_hal_id",
    "parse_hal_doc",
    "resolve_struct_id",
    "search",
    "search_by_structure",
]
