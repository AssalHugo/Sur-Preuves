"""Tests unitaires pour la modélisation et le parsing OpenAlex."""

from typing import Any

from csc.connectors.openalex.models import (
    author_dict_to_author,
    institution_dict_to_institution,
    normalize_doi,
    normalize_openalex_id,
    reconstruct_abstract,
    work_dict_to_scholarly_work,
)
from csc.contracts.models import ScholarlyWork


def test_reconstruct_abstract_nominal() -> None:
    inverted_index = {
        "This": [0],
        "is": [1],
        "a": [2],
        "test": [3],
        "abstract.": [4],
    }
    result = reconstruct_abstract(inverted_index)
    assert result == "This is a test abstract."


def test_reconstruct_abstract_out_of_order_and_multiple() -> None:
    inverted_index = {
        "tax": [1, 5],
        "Carbon": [0],
        "reduces": [2],
        "emissions,": [3],
        "yes": [4],
        "works.": [6],
    }
    result = reconstruct_abstract(inverted_index)
    assert result == "Carbon tax reduces emissions, yes tax works."


def test_reconstruct_abstract_empty_or_none() -> None:
    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


def test_normalize_doi() -> None:
    assert normalize_doi("https://doi.org/10.1038/s41558-019-0401-7") == "10.1038/s41558-019-0401-7"
    assert normalize_doi("http://doi.org/10.1016/j.test") == "10.1016/j.test"
    assert normalize_doi("https://dx.doi.org/10.1111/xyz") == "10.1111/xyz"
    assert normalize_doi("doi:10.1007/s10640") == "10.1007/s10640"
    assert normalize_doi("10.1038/NATURE1234") == "10.1038/nature1234"
    assert normalize_doi(None) is None
    assert normalize_doi("   ") is None


def test_normalize_openalex_id() -> None:
    assert normalize_openalex_id("https://openalex.org/W2741809807") == "W2741809807"
    assert normalize_openalex_id("https://openalex.org/I136199984") == "I136199984"
    assert normalize_openalex_id("A5012345678") == "A5012345678"
    assert normalize_openalex_id("https://openalex.org/topics/T11636") == "T11636"
    assert normalize_openalex_id("https://api.openalex.org/works/W2741809807") == "W2741809807"
    assert normalize_openalex_id("works/W2741809807") == "W2741809807"
    assert normalize_openalex_id(None) is None
    assert normalize_openalex_id("   ") is None


def test_work_dict_to_scholarly_work_single(load_cassette: Any) -> None:
    raw_work = load_cassette("single_work")
    work = work_dict_to_scholarly_work(raw_work)

    assert isinstance(work, ScholarlyWork)
    assert work.doi == "10.1038/s41558-019-0401-7"
    assert work.openalex_id == "W2741809807"
    assert work.title == "Measuring the macroeconomic impact of carbon taxes"
    assert work.year == 2020
    assert work.venue == "Nature Climate Change"
    assert work.cited_by_count == 412
    assert work.abstract is not None
    assert "macroeconomic impacts of carbon tax" in work.abstract
    assert len(work.authors) == 2
    assert "Gilbert E. Metcalf" in work.authors
    assert "James H. Stock" in work.authors
    assert work.is_systematic_review is False
    assert work.url == "https://doi.org/10.1038/s41558-019-0401-7"


def test_work_dict_to_scholarly_work_review_detection() -> None:
    # Cas 1 : type == 'review'
    data_review = {
        "id": "W111",
        "title": "A general survey of climate policies",
        "type": "review",
    }
    work1 = work_dict_to_scholarly_work(data_review)
    assert work1.is_systematic_review is True

    # Cas 2 : titre avec meta-analysis
    data_meta = {
        "id": "W222",
        "title": "Employment effects of environmental policy: A meta-analysis",
        "type": "article",
    }
    work2 = work_dict_to_scholarly_work(data_meta)
    assert work2.is_systematic_review is True

    # Cas 3 : résumé avec systematic review
    data_abstract = {
        "id": "W333",
        "title": "Clean energy transitions",
        "type": "article",
        "abstract_inverted_index": {
            "A": [0],
            "systematic": [1],
            "review": [2],
            "of": [3],
            "evidence.": [4],
        },
    }
    work3 = work_dict_to_scholarly_work(data_abstract)
    assert work3.is_systematic_review is True


def test_work_dict_edge_cases() -> None:
    # Sans titre et année aberrante
    data = {
        "id": "W999",
        "title": "",
        "publication_year": 1750,
    }
    work = work_dict_to_scholarly_work(data)
    assert work.title == "[Sans titre]"
    assert work.year is None


def test_institution_dict_to_institution(load_cassette: Any) -> None:
    payload = load_cassette("institutions")
    raw_inst = payload["results"][0]
    inst = institution_dict_to_institution(raw_inst)

    assert inst.id == "I136199984"
    assert inst.display_name == "Harvard University"
    assert inst.country_code == "US"
    assert inst.type == "education"
    assert inst.ror == "https://ror.org/03vek6s52"
    assert inst.works_count == 254120
    assert inst.cited_by_count == 8901234
    assert inst.homepage_url == "https://www.harvard.edu"


def test_author_dict_to_author(load_cassette: Any) -> None:
    payload = load_cassette("authors")
    raw_author = payload["results"][0]
    author = author_dict_to_author(raw_author)

    assert author.id == "A5012345678"
    assert author.display_name == "Gilbert E. Metcalf"
    assert author.orcid == "https://orcid.org/0000-0002-1234-5678"
    assert author.works_count == 142
    assert author.cited_by_count == 9820
    assert author.last_known_institution == "Tufts University"
    assert author.last_known_institution_id == "I12180000"
