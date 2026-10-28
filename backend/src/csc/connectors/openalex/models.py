"""Modèles de données et transformateurs pour le connecteur OpenAlex."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from csc.contracts.models import ScholarlyWork
from csc.contracts.uuid_v7 import uuid7


class Institution(BaseModel):
    """Représentation d'une institution de recherche selon OpenAlex."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Identifiant OpenAlex de l'institution (ex: I136199984)")
    display_name: str = Field(description="Nom complet de l'établissement")
    country_code: str | None = Field(default=None, description="Code pays ISO à deux lettres")
    type: str | None = Field(
        default=None, description="Type d'institution (education, facility, government...)"
    )
    ror: str | None = Field(default=None, description="Identifiant ROR de l'institution")
    works_count: int = Field(default=0, ge=0, description="Nombre total de publications associées")
    cited_by_count: int = Field(default=0, ge=0, description="Nombre total de citations reçues")
    homepage_url: str | None = Field(default=None, description="URL du site officiel")


class Author(BaseModel):
    """Représentation d'un chercheur selon OpenAlex (repérage de relecteurs L00)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Identifiant OpenAlex de l'auteur (ex: A5000000000)")
    display_name: str = Field(description="Nom complet du chercheur")
    orcid: str | None = Field(default=None, description="Identifiant ORCID normalisé")
    works_count: int = Field(default=0, ge=0, description="Nombre total de publications")
    cited_by_count: int = Field(default=0, ge=0, description="Nombre total de citations")
    last_known_institution: str | None = Field(
        default=None, description="Nom de la dernière institution d'affiliation connue"
    )
    last_known_institution_id: str | None = Field(
        default=None, description="Identifiant OpenAlex de la dernière institution connue"
    )


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Reconstitue le texte brut d'un résumé scientifique à partir de l'abstract_inverted_index.

    Dans l'API OpenAlex, les résumés sont stockés sous forme d'index inversé associant
    chaque mot à ses positions ordinales dans le texte.
    """
    if not inverted_index:
        return None

    position_to_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            position_to_word[pos] = word

    if not position_to_word:
        return None

    sorted_positions = sorted(position_to_word.keys())
    return " ".join(position_to_word[pos] for pos in sorted_positions)


def normalize_doi(doi: str | None) -> str | None:
    """Normalise un DOI en supprimant les préfixes d'URL usuels."""
    if not doi:
        return None
    d = doi.strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if d.lower().startswith(prefix):
            d = d[len(prefix) :].strip()
    return d.lower() if d else None


def normalize_openalex_id(openalex_id: str | None) -> str | None:
    """Normalise un identifiant OpenAlex en ne conservant que l'ID court (ex: W12345, T11636)."""
    if not openalex_id:
        return None
    s = openalex_id.strip().rstrip("/")
    if not s:
        return None
    s = s.split("/")[-1]
    return s.strip() if s else None


def work_dict_to_scholarly_work(data: dict[str, Any]) -> ScholarlyWork:
    """Convertit un dictionnaire de résultat OpenAlex en instance ScholarlyWork."""
    title = (data.get("title") or "").strip()
    if not title:
        title = "[Sans titre]"

    year = data.get("publication_year")
    if year is not None:
        try:
            year = int(year)
            if year < 1800 or year > 2100:
                year = None
        except (ValueError, TypeError):
            year = None

    venue: str | None = None
    primary_location = data.get("primary_location")
    if isinstance(primary_location, dict):
        source = primary_location.get("source")
        if isinstance(source, dict):
            venue = source.get("display_name")
    if not venue:
        host_venue = data.get("host_venue")
        if isinstance(host_venue, dict):
            venue = host_venue.get("display_name")

    # Reconstruction de l'abstract
    inverted_index = data.get("abstract_inverted_index")
    abstract = reconstruct_abstract(inverted_index) or data.get("abstract")

    # Auteurs
    authors: list[str] = []
    for authorship in data.get("authorships") or []:
        if isinstance(authorship, dict):
            author_info = authorship.get("author")
            if isinstance(author_info, dict):
                author_name = author_info.get("display_name")
                if author_name and isinstance(author_name, str):
                    authors.append(author_name.strip())

    # Détection des revues systématiques et méta-analyses
    work_type = str(data.get("type") or "").lower()
    title_lower = title.lower()
    abstract_lower = (abstract or "").lower()
    is_review = (
        work_type == "review"
        or "meta-analysis" in title_lower
        or "méta-analyse" in title_lower
        or "systematic review" in title_lower
        or "revue systématique" in title_lower
        or "meta-analysis" in abstract_lower
        or "systematic review" in abstract_lower
    )

    doi = normalize_doi(data.get("doi"))
    openalex_id = normalize_openalex_id(data.get("id"))

    # Détermination de l'URL d'accès
    url: str | None = None
    if data.get("doi"):
        url = str(data.get("doi"))
    elif isinstance(primary_location, dict) and primary_location.get("landing_page_url"):
        url = str(primary_location.get("landing_page_url"))
    elif data.get("id"):
        url = str(data.get("id"))

    return ScholarlyWork(
        id=uuid7(),
        doi=doi,
        openalex_id=openalex_id,
        hal_id=None,
        s2_id=None,
        title=title,
        year=year,
        venue=venue,
        cited_by_count=int(data.get("cited_by_count") or 0),
        abstract=abstract,
        design=None,
        sms_level=None,
        is_systematic_review=is_review,
        authors=authors,
        url=url,
    )


def institution_dict_to_institution(data: dict[str, Any]) -> Institution:
    """Convertit un dictionnaire OpenAlex en modèle Institution."""
    return Institution(
        id=normalize_openalex_id(data.get("id")) or str(data.get("id") or ""),
        display_name=str(data.get("display_name") or "[Sans nom]"),
        country_code=data.get("country_code"),
        type=data.get("type"),
        ror=data.get("ror"),
        works_count=int(data.get("works_count") or 0),
        cited_by_count=int(data.get("cited_by_count") or 0),
        homepage_url=data.get("homepage_url"),
    )


def author_dict_to_author(data: dict[str, Any]) -> Author:
    """Convertit un dictionnaire OpenAlex en modèle Author."""
    last_inst_name: str | None = None
    last_inst_id: str | None = None

    last_known = data.get("last_known_institution")
    if isinstance(last_known, dict):
        last_inst_name = last_known.get("display_name")
        last_inst_id = normalize_openalex_id(last_known.get("id"))
    elif isinstance(data.get("last_known_institutions"), list) and data["last_known_institutions"]:
        first_inst = data["last_known_institutions"][0]
        if isinstance(first_inst, dict):
            last_inst_name = first_inst.get("display_name")
            last_inst_id = normalize_openalex_id(first_inst.get("id"))

    return Author(
        id=normalize_openalex_id(data.get("id")) or str(data.get("id") or ""),
        display_name=str(data.get("display_name") or "[Sans nom]"),
        orcid=data.get("orcid"),
        works_count=int(data.get("works_count") or 0),
        cited_by_count=int(data.get("cited_by_count") or 0),
        last_known_institution=last_inst_name,
        last_known_institution_id=last_inst_id,
    )
