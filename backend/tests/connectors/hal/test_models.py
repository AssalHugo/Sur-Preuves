"""Tests unitaires des modèles, normalisations et utilitaires HAL."""

from typing import Any

import pytest

from csc.connectors.hal.models import (
    KNOWN_STRUCTURES,
    build_proximity_query,
    escape_solr_phrase_term,
    normalize_doi,
    normalize_hal_id,
    parse_hal_doc,
    resolve_struct_id,
)


def test_build_proximity_query_nominal() -> None:
    clause = build_proximity_query("taxe", "carbone", 3)
    assert clause == '"taxe carbone"~3'


def test_build_proximity_query_escaping_quotes_and_backslashes() -> None:
    clause = build_proximity_query('taxe "verte"', "co2\\ghg", 2)
    assert clause == '"taxe \\"verte\\" co2\\\\ghg"~2'


def test_build_proximity_query_negative_distance() -> None:
    clause = build_proximity_query("climat", "rechauffement", -5)
    assert clause == '"climat rechauffement"~0'


def test_escape_solr_phrase_term_whitespace() -> None:
    escaped = escape_solr_phrase_term("  energie   solaire \n propre ")
    assert escaped == "energie solaire propre"


def test_normalize_doi_cases() -> None:
    assert normalize_doi("10.1070/RM9982") == "10.1070/rm9982"
    assert normalize_doi("https://doi.org/10.3917/MAV.124.0151/") == "10.3917/mav.124.0151"
    assert normalize_doi("http://dx.doi.org/10.1000/182") == "10.1000/182"
    assert normalize_doi("doi:10.1234/ABC") == "10.1234/abc"
    assert normalize_doi(["10.5678/XYZ"]) == "10.5678/xyz"
    assert normalize_doi([]) is None
    assert normalize_doi(None) is None
    assert normalize_doi("   ") is None


def test_normalize_hal_id_cases() -> None:
    assert normalize_hal_id("halshs-00557065v1") == "halshs-00557065"
    assert normalize_hal_id("https://shs.hal.science/halshs-00557065v2") == "halshs-00557065"
    assert normalize_hal_id("https://hal.science/hal-03707816/") == "hal-03707816"
    assert normalize_hal_id("tel-00984266v1") == "tel-00984266"
    assert normalize_hal_id(["hal-01234567v3"]) == "hal-01234567"
    assert normalize_hal_id([]) is None
    assert normalize_hal_id(None) is None
    assert normalize_hal_id("   ") is None


def test_resolve_struct_id_cases() -> None:
    assert "IPP" in KNOWN_STRUCTURES
    assert "OFCE" in KNOWN_STRUCTURES
    assert "INRAE" in KNOWN_STRUCTURES
    assert "LIEPP" in KNOWN_STRUCTURES
    assert resolve_struct_id("IPP") == 266522
    assert resolve_struct_id("ipp") == 266522
    assert resolve_struct_id("OFCE") == 250936
    assert resolve_struct_id("INRAE") == 577435
    assert resolve_struct_id("CNRS-SHS") == 84039
    assert resolve_struct_id("LIEPP") == 218465
    assert resolve_struct_id(266522) == 266522
    assert resolve_struct_id("266522") == 266522

    with pytest.raises(ValueError, match="inconnue du référentiel"):
        resolve_struct_id("UNKNOWN_STRUCT_XYZ")


def test_parse_hal_doc_with_doi(load_hal_cassette: Any) -> None:
    cassette = load_hal_cassette("single_work_with_doi")
    doc = cassette["response"]["docs"][0]

    work = parse_hal_doc(doc)
    assert work.hal_id == "halshs-03386384"
    assert work.doi == "10.3917/mav.124.0151"
    assert "Pilotage stratégique de la taxe carbone" in work.title
    assert work.year == 2021
    assert work.venue == "Revue management & avenir"
    assert "Marco Heimann" in work.authors
    assert "Katia Lobre-Lebraty" in work.authors
    assert work.url == "https://shs.hal.science/halshs-03386384v1"
    assert work.abstract is not None
    assert "Cette recherche s’intéresse à l’opinion" in work.abstract
    assert work.cited_by_count == 0


def test_parse_hal_doc_without_doi(load_hal_cassette: Any) -> None:
    cassette = load_hal_cassette("single_work_no_doi")
    doc = cassette["response"]["docs"][0]

    work = parse_hal_doc(doc)
    assert work.hal_id == "hal-03473891"
    assert work.doi is None
    assert "De Rio à Rio" in work.title
    assert work.year == 2012
    assert "Eloi Laurent" in work.authors
    assert "Observatoire français des conjonctures économiques" in (work.venue or "")
    assert work.url == "https://sciencespo.hal.science/hal-03473891v1"


def test_parse_hal_doc_multilingual_abstract_and_systematic_review() -> None:
    raw_doc = {
        "halId_s": "hal-09999999",
        "title_s": ["Systematic review of carbon taxation impacts", "Revue systématique"],
        "abstract_s": [
            "Ce document propose une méta-analyse quantitative.",
            "This document provides a systematic review and meta-analysis.",
        ],
        "authFullName_s": ["Alice Dupont", "Alice Dupont", "Bob Martin"],
        "docType_s": "ART",
        "producedDateY_i": 2023,
        "journalTitle_s": "Journal of Environmental Economics",
        "uri_s": "https://hal.science/hal-09999999",
    }

    work = parse_hal_doc(raw_doc)
    assert work.title == "Systematic review of carbon taxation impacts"
    assert work.is_systematic_review is True
    assert work.authors == ["Alice Dupont", "Bob Martin"]  # dédupliqué
    assert work.abstract is not None
    assert "Ce document propose une méta-analyse quantitative." in work.abstract
    assert "This document provides a systematic review and meta-analysis." in work.abstract
    assert work.year == 2023
    assert work.venue == "Journal of Environmental Economics"


def test_parse_hal_doc_these_and_report_fallbacks() -> None:
    thesis_doc = {
        "halId_s": "tel-01234567",
        "title_s": "Thèse d'économie sur la taxe carbone",
        "docType_s": "THESE",
        "structName_s": ["Centre d'économie de la Sorbonne"],
        "producedDateY_i": 2020,
    }
    work_thesis = parse_hal_doc(thesis_doc)
    assert work_thesis.venue == "Thèse de doctorat (Centre d'économie de la Sorbonne)"

    report_doc = {
        "halId_s": "hal-report-01",
        "title_s": "Rapport annuel sur le climat",
        "docType_s": "REPORT",
        "structName_s": ["Institut des Politiques Publiques"],
        "producedDateY_i": 2022,
    }
    work_report = parse_hal_doc(report_doc)
    assert work_report.venue == "Institut des Politiques Publiques"
