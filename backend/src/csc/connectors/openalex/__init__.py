"""Connecteur OpenAlex pour la recherche documentaire scientifique."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from csc.connectors.openalex.budget import OpenAlexBudgetManager
from csc.connectors.openalex.cache import OpenAlexHttpCache
from csc.connectors.openalex.client import OpenAlexClient
from csc.connectors.openalex.exceptions import (
    OpenAlexApiError,
    OpenAlexBudgetExceededError,
    OpenAlexError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)
from csc.connectors.openalex.models import (
    Author,
    Institution,
    normalize_doi,
    normalize_openalex_id,
    reconstruct_abstract,
)
from csc.connectors.openalex.rate_limiter import OpenAlexRateLimiter
from csc.contracts.models import ScholarlyWork

_default_client: OpenAlexClient | None = None


def get_default_client() -> OpenAlexClient:
    """Retourne l'instance singleton par défaut du client OpenAlex."""
    global _default_client
    if _default_client is None:
        _default_client = OpenAlexClient()
    return _default_client


def search_works(
    query: str = "",
    *,
    filters: dict[str, Any] | None = None,
    sort: str = "cited_by_count:desc",
    per_page: int = 50,
    max_results: int = 200,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[ScholarlyWork]:
    """Recherche des travaux scientifiques sur OpenAlex."""
    return get_default_client().search_works(
        query=query,
        filters=filters,
        sort=sort,
        per_page=per_page,
        max_results=max_results,
        claim_id=claim_id,
        session=session,
    )


def semantic_search_works(
    text: str,
    *,
    filters: dict[str, Any] | None = None,
    k: int = 50,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[ScholarlyWork]:
    """Recherche sémantique de travaux scientifiques par similarité conceptuelle."""
    return get_default_client().semantic_search_works(
        text=text,
        filters=filters,
        k=k,
        claim_id=claim_id,
        session=session,
    )


def get_work(
    id_or_doi: str,
    *,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> ScholarlyWork:
    """Récupère une publication scientifique par son DOI ou son identifiant OpenAlex."""
    return get_default_client().get_work(
        id_or_doi=id_or_doi,
        claim_id=claim_id,
        session=session,
    )


def find_systematic_reviews(
    topic_query: str,
    *,
    since_year: int = 2005,
    sort: str = "cited_by_count:desc",
    per_page: int = 50,
    max_results: int = 100,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[ScholarlyWork]:
    """Recherche spécifiquement les revues systématiques et méta-analyses."""
    return get_default_client().find_systematic_reviews(
        topic_query=topic_query,
        since_year=since_year,
        sort=sort,
        per_page=per_page,
        max_results=max_results,
        claim_id=claim_id,
        session=session,
    )


def top_institutions(
    topic_id: str,
    n: int = 3,
    *,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[Institution]:
    """Identifie les institutions les plus influentes sur un sujet."""
    return get_default_client().top_institutions(
        topic_id=topic_id,
        n=n,
        claim_id=claim_id,
        session=session,
    )


def top_authors(
    topic_id: str,
    n: int = 20,
    *,
    claim_id: UUID | None = None,
    session: Session | None = None,
) -> list[Author]:
    """Identifie les auteurs majeurs sur un sujet."""
    return get_default_client().top_authors(
        topic_id=topic_id,
        n=n,
        claim_id=claim_id,
        session=session,
    )


__all__ = [
    "Author",
    "Institution",
    "OpenAlexApiError",
    "OpenAlexBudgetExceededError",
    "OpenAlexBudgetManager",
    "OpenAlexClient",
    "OpenAlexError",
    "OpenAlexHttpCache",
    "OpenAlexNotFoundError",
    "OpenAlexRateLimitError",
    "OpenAlexRateLimiter",
    "find_systematic_reviews",
    "get_default_client",
    "get_work",
    "normalize_doi",
    "normalize_openalex_id",
    "reconstruct_abstract",
    "search_works",
    "semantic_search_works",
    "top_authors",
    "top_institutions",
]
