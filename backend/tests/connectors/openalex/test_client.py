"""Tests d'intégration et unitaires pour le client OpenAlex avec respx (zéro réseau)."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response
from sqlalchemy.orm import Session

from csc.connectors.openalex.budget import OpenAlexBudgetManager
from csc.connectors.openalex.cache import OpenAlexHttpCache
from csc.connectors.openalex.client import OpenAlexClient
from csc.connectors.openalex.exceptions import (
    OpenAlexApiError,
    OpenAlexNotFoundError,
    OpenAlexRateLimitError,
)
from csc.connectors.openalex.rate_limiter import OpenAlexRateLimiter
from csc.contracts.uuid_v7 import uuid7
from csc.db.models import EvidenceQueryModel


@pytest.fixture
def mock_openalex_client(
    tmp_openalex_cache: OpenAlexHttpCache,
    tmp_budget_manager: OpenAlexBudgetManager,
) -> OpenAlexClient:
    """Fournit un client OpenAlex configuré pour les tests hors ligne."""
    limiter = OpenAlexRateLimiter(general_rate=100.0, semantic_rate=100.0)
    return OpenAlexClient(
        api_key="TEST_API_KEY",
        cache=tmp_openalex_cache,
        rate_limiter=limiter,
        budget_manager=tmp_budget_manager,
        backoff_factor=0.01,
        max_retries=2,
    )


@respx.mock
def test_search_works_nominal(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("works_search")
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=Response(
            200,
            json=cassette,
            headers={
                "x-ratelimit-credits-used": "2.5",
                "x-ratelimit-remaining": "99900",
                "x-ratelimit-limit": "100000",
            },
        )
    )

    works = mock_openalex_client.search_works(
        query="carbon tax employment",
        sort="cited_by_count:desc",
        max_results=5,
    )

    assert route.called
    assert len(works) == 5
    assert works[0].cited_by_count >= works[1].cited_by_count
    assert "Study on carbon tax" in works[0].title

    # Vérification EvidenceQuery
    assert len(mock_openalex_client.recorded_queries) == 1
    query_record = mock_openalex_client.recorded_queries[0]
    assert query_record.source == "openalex"
    assert query_record.parameters["credits_used"] == 2.5
    assert query_record.parameters["cached"] is False


@respx.mock
def test_cursor_pagination(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    page1 = load_cassette("cursor_page1")
    page2 = load_cassette("cursor_page2")

    route = respx.get("https://api.openalex.org/works")
    # Premier appel avec cursor=* renvoie page1 avec next_cursor
    route.side_effect = [
        Response(200, json=page1, headers={"x-ratelimit-credits-used": "1.0"}),
        Response(200, json=page2, headers={"x-ratelimit-credits-used": "1.0"}),
    ]

    works = mock_openalex_client.search_works(
        query="carbon tax",
        per_page=3,
        max_results=5,
    )

    assert route.call_count == 2
    # Vérification des paramètres des requêtes
    first_call = route.calls[0]
    second_call = route.calls[1]
    assert first_call.request.url.params["cursor"] == "*"
    assert second_call.request.url.params["cursor"] == "CURSOR_TOKEN_ABC123"

    assert len(works) == 5


@respx.mock
def test_get_work_by_doi_and_id(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("single_work")
    doi_route = respx.get(
        "https://api.openalex.org/works/https://doi.org/10.1038/s41558-019-0401-7"
    ).mock(return_value=Response(200, json=cassette))

    id_route = respx.get("https://api.openalex.org/works/W2741809807").mock(
        return_value=Response(200, json=cassette)
    )

    # Recherche par DOI
    work_doi = mock_openalex_client.get_work("10.1038/s41558-019-0401-7")
    assert doi_route.called
    assert work_doi.doi == "10.1038/s41558-019-0401-7"

    # Recherche par ID
    work_id = mock_openalex_client.get_work("W2741809807")
    assert id_route.called
    assert work_id.openalex_id == "W2741809807"


@respx.mock
def test_get_work_not_found(mock_openalex_client: OpenAlexClient) -> None:
    respx.get("https://api.openalex.org/works/W000000").mock(
        return_value=Response(404, json={"error": "Not found"})
    )

    with pytest.raises(OpenAlexNotFoundError) as exc_info:
        mock_openalex_client.get_work("W000000")
    assert "HTTP 404" in str(exc_info.value)


@respx.mock
def test_find_systematic_reviews(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("reviews_search")
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=Response(200, json=cassette)
    )

    reviews = mock_openalex_client.find_systematic_reviews(
        topic_query="carbon tax employment",
        since_year=2015,
        max_results=10,
    )

    assert route.called
    assert len(reviews) == 10
    # Vérifie que le filtre type:review a été injecté
    call = route.calls[0]
    filter_param = call.request.url.params["filter"]
    assert "type:review" in filter_param
    assert "from_publication_date:2015-01-01" in filter_param

    for rev in reviews:
        assert rev.is_systematic_review is True


@respx.mock
def test_semantic_search_works(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("works_search")
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=Response(200, json=cassette)
    )

    results = mock_openalex_client.semantic_search_works(
        text="Impact of environmental taxation on wage shifting",
        k=3,
    )

    assert route.called
    assert len(results) == 3


@respx.mock
def test_top_institutions(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("institutions")
    route = respx.get("https://api.openalex.org/institutions").mock(
        return_value=Response(200, json=cassette)
    )

    institutions = mock_openalex_client.top_institutions("T11636", n=3)
    assert route.called
    assert len(institutions) == 3
    assert institutions[0].display_name == "Harvard University"
    assert institutions[0].country_code == "US"


@respx.mock
def test_top_authors(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("authors")
    route = respx.get("https://api.openalex.org/authors").mock(
        return_value=Response(200, json=cassette)
    )

    authors = mock_openalex_client.top_authors("T11636", n=3)
    assert route.called
    assert len(authors) == 3
    assert authors[0].display_name == "Gilbert E. Metcalf"
    assert authors[0].last_known_institution == "Tufts University"


@respx.mock
def test_retry_on_429_success(mock_openalex_client: OpenAlexClient, load_cassette: Any) -> None:
    cassette = load_cassette("single_work")
    route = respx.get("https://api.openalex.org/works/W2741809807")
    # Premier appel 429, second appel 200
    route.side_effect = [
        Response(429, headers={"retry-after": "0.01"}),
        Response(200, json=cassette),
    ]

    work = mock_openalex_client.get_work("W2741809807")
    assert route.call_count == 2
    assert work.openalex_id == "W2741809807"


@respx.mock
def test_retry_on_429_exhausted(mock_openalex_client: OpenAlexClient) -> None:
    respx.get("https://api.openalex.org/works/W2741809807").mock(
        return_value=Response(429, headers={"retry-after": "0.01"})
    )

    with pytest.raises(OpenAlexRateLimitError) as exc_info:
        mock_openalex_client.get_work("W2741809807")
    assert "HTTP 429" in str(exc_info.value)


@respx.mock
def test_retry_on_500_server_error(
    mock_openalex_client: OpenAlexClient, load_cassette: Any
) -> None:
    cassette = load_cassette("single_work")
    route = respx.get("https://api.openalex.org/works/W2741809807")
    # 503 puis 200
    route.side_effect = [
        Response(503),
        Response(200, json=cassette),
    ]

    work = mock_openalex_client.get_work("W2741809807")
    assert route.call_count == 2
    assert work.openalex_id == "W2741809807"


@respx.mock
def test_retry_on_500_exhausted(mock_openalex_client: OpenAlexClient) -> None:
    respx.get("https://api.openalex.org/works/W2741809807").mock(return_value=Response(500))

    with pytest.raises(OpenAlexApiError) as exc_info:
        mock_openalex_client.get_work("W2741809807")
    assert "HTTP 500" in str(exc_info.value)


@respx.mock
def test_http_cache_prevents_network_call(
    mock_openalex_client: OpenAlexClient, load_cassette: Any
) -> None:
    cassette = load_cassette("single_work")
    route = respx.get("https://api.openalex.org/works/W2741809807").mock(
        return_value=Response(200, json=cassette, headers={"x-ratelimit-credits-used": "1.0"})
    )

    # 1er appel : va sur le réseau
    work1 = mock_openalex_client.get_work("W2741809807")
    assert route.call_count == 1
    assert work1.openalex_id == "W2741809807"

    # 2e appel : servi depuis le cache, aucun appel réseau supplémentaire
    work2 = mock_openalex_client.get_work("W2741809807")
    assert route.call_count == 1
    assert work2.openalex_id == "W2741809807"

    # Vérification que la 2e requête est bien marquée comme cached dans EvidenceQuery
    assert len(mock_openalex_client.recorded_queries) == 2
    assert mock_openalex_client.recorded_queries[0].parameters["cached"] is False
    assert mock_openalex_client.recorded_queries[1].parameters["cached"] is True
    assert mock_openalex_client.recorded_queries[1].parameters["credits_used"] == 0.0


@respx.mock
def test_evidence_query_database_persistence(
    mock_openalex_client: OpenAlexClient,
    load_cassette: Any,
) -> None:
    cassette = load_cassette("single_work")
    respx.get("https://api.openalex.org/works/W2741809807").mock(
        return_value=Response(200, json=cassette)
    )

    mock_session = MagicMock(spec=Session)
    claim_id = uuid7()

    work = mock_openalex_client.get_work(
        "W2741809807",
        claim_id=claim_id,
        session=mock_session,
    )
    assert work.openalex_id == "W2741809807"

    # Vérifier que l'EvidenceQueryModel a été ajouté à la session et flushé
    assert mock_session.add.called
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, EvidenceQueryModel)
    assert added_obj.claim_id == claim_id
    assert added_obj.source == "openalex"
    assert added_obj.results_count == 1
    assert "W2741809807" in added_obj.exact_query
    assert mock_session.flush.called


@respx.mock
def test_get_work_by_uppercase_doi(
    mock_openalex_client: OpenAlexClient, load_cassette: Any
) -> None:
    cassette = load_cassette("single_work")
    doi_route = respx.get(
        "https://api.openalex.org/works/https://doi.org/10.1038/s41558-019-0401-7"
    ).mock(return_value=Response(200, json=cassette))

    work1 = mock_openalex_client.get_work("DOI:10.1038/S41558-019-0401-7")
    assert doi_route.called
    assert work1.doi == "10.1038/s41558-019-0401-7"

    # Vérification avec URL en majuscules
    work2 = mock_openalex_client.get_work("HTTPS://DOI.ORG/10.1038/S41558-019-0401-7")
    assert work2.doi == "10.1038/s41558-019-0401-7"


def test_client_context_manager_and_query_eviction(
    mock_openalex_client: OpenAlexClient,
) -> None:
    with mock_openalex_client as client:
        assert client._get_http_client() is not None
        assert not client._get_http_client().is_closed

    assert client._client is not None
    assert client._client.is_closed

    # Test d'éviction et nettoyage des requêtes en mémoire
    for i in range(1005):
        client._record_evidence_query(
            exact_query=f"query_{i}",
            parameters={},
            results_count=1,
        )

    assert len(client.recorded_queries) == 1000
    assert client.recorded_queries[0].exact_query == "query_5"
    assert client.recorded_queries[-1].exact_query == "query_1004"

    client.clear_recorded_queries()
    assert len(client.recorded_queries) == 0
