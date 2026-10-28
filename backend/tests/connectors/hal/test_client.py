"""Tests unitaires et d'intégration pour le client HAL (zéro appel réseau)."""

from typing import Any
from unittest.mock import MagicMock

import pytest
import respx
from httpx import Response
from sqlalchemy.orm import Session

from csc.connectors.hal.client import DEFAULT_FL_FIELDS, HalClient
from csc.connectors.hal.exceptions import (
    HalApiError,
    HalNotFoundError,
    HalRateLimitError,
)
from csc.contracts.uuid_v7 import uuid7
from csc.db.models import EvidenceQueryModel


@respx.mock
def test_search_nominal_and_proximity_acceptance(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("search_proximity")
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    works = mock_hal_client.search(
        query="taxe carbone",
        proximity=("taxe", "carbone", 3),
        doc_types=("ART", "REPORT", "THESE", "COUV"),
        since_year=2005,
        rows=5,
    )

    assert route.called
    req = route.calls.last.request
    params = req.url.params

    # Critères d'acceptation : requête de proximité échappée, filtres type et année
    assert params["q"] == '"taxe carbone"~3'
    fq_list = params.get_list("fq")
    assert any("docType_s:(ART OR REPORT OR THESE OR COUV)" in fq for fq in fq_list)
    assert any("producedDateY_i:[2005 TO *]" in fq for fq in fq_list)
    assert params["fl"] == DEFAULT_FL_FIELDS
    assert params["rows"] == "5"

    # Vérification du parsing
    assert len(works) == 5
    first_work = works[0]
    assert first_work.hal_id == "halshs-00557065"
    assert "Fallait-il appliquer la taxe carbone" in first_work.title
    assert first_work.year == 2010
    assert first_work.venue == "Flux - Cahiers scientifiques internationaux Réseaux et territoires"
    assert "Richard Darbéra" in first_work.authors

    # Traçabilité EvidenceQuery
    assert len(mock_hal_client.recorded_queries) == 1
    query_record = mock_hal_client.recorded_queries[0]
    assert query_record.source == "hal"
    assert query_record.results_count == 5
    assert query_record.parameters.get("cached") is False


@respx.mock
def test_search_by_structure(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("search_structure")
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    works = mock_hal_client.search_by_structure(
        struct_ids=[266522, 250936],
        query="carbone",
        rows=5,
    )

    assert route.called
    req = route.calls.last.request
    params = req.url.params
    assert params["q"] == "carbone"
    fq_list = params.get_list("fq")
    assert any("structId_i:(266522 OR 250936)" in fq for fq in fq_list)

    assert len(works) == 5
    assert all(w.hal_id is not None for w in works)


@respx.mock
def test_get_nominal_and_version_normalization(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    work = mock_hal_client.get("halshs-03386384v1")

    assert route.called
    req = route.calls.last.request
    assert req.url.params["q"] == 'halId_s:"halshs-03386384"'

    assert work.hal_id == "halshs-03386384"
    assert work.doi == "10.3917/mav.124.0151"
    assert "Pilotage stratégique de la taxe carbone" in work.title


@respx.mock
def test_get_not_found(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("empty_search")
    respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    with pytest.raises(HalNotFoundError, match="introuvable"):
        mock_hal_client.get("hal-non-existent-99999999")


@respx.mock
def test_retry_on_429_success(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        side_effect=[
            Response(429, headers={"retry-after": "0.01"}),
            Response(200, json=cassette),
        ]
    )

    work = mock_hal_client.get("halshs-03386384")
    assert work.hal_id == "halshs-03386384"
    assert route.call_count == 2


@respx.mock
def test_retry_on_429_exhausted(mock_hal_client: HalClient) -> None:
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(429, headers={"retry-after": "0.01"})
    )

    with pytest.raises(HalRateLimitError, match="HTTP 429"):
        mock_hal_client.get("halshs-03386384")

    assert route.call_count == mock_hal_client.max_retries + 1


@respx.mock
def test_retry_on_500_server_error(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        side_effect=[
            Response(502),
            Response(200, json=cassette),
        ]
    )

    work = mock_hal_client.get("halshs-03386384")
    assert work.hal_id == "halshs-03386384"
    assert route.call_count == 2


@respx.mock
def test_retry_on_500_exhausted(mock_hal_client: HalClient) -> None:
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(return_value=Response(500))

    with pytest.raises(HalApiError, match="HTTP 500"):
        mock_hal_client.get("halshs-03386384")

    assert route.call_count == mock_hal_client.max_retries + 1


@respx.mock
def test_http_cache_prevents_network_call(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    route = respx.get("https://api.archives-ouvertes.fr/search").mock(
        return_value=Response(200, json=cassette)
    )

    # 1er appel : appel réseau et mise en cache
    work1 = mock_hal_client.get("halshs-03386384")
    assert route.call_count == 1
    assert mock_hal_client.recorded_queries[-1].parameters["cached"] is False

    # 2nd appel : servi depuis le cache, aucun appel réseau supplémentaire
    work2 = mock_hal_client.get("halshs-03386384")
    assert route.call_count == 1
    assert work1.title == work2.title
    assert mock_hal_client.recorded_queries[-1].parameters["cached"] is True


def test_evidence_query_database_persistence(
    mock_hal_client: HalClient,
    load_hal_cassette: Any,
) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    with respx.mock:
        respx.get("https://api.archives-ouvertes.fr/search").mock(
            return_value=Response(200, json=cassette)
        )

        mock_session = MagicMock(spec=Session)
        claim_id = uuid7()

        mock_hal_client.get(
            "halshs-03386384",
            claim_id=claim_id,
            session=mock_session,
        )

        assert mock_session.add.called
        assert mock_session.flush.called
        added_arg = mock_session.add.call_args[0][0]
        assert isinstance(added_arg, EvidenceQueryModel)
        assert added_arg.source == "hal"
        assert added_arg.claim_id == claim_id


def test_client_context_manager() -> None:
    with HalClient() as client:
        assert client is not None
