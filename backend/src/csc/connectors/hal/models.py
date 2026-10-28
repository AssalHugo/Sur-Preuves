"""Modèles, normalisations et utilitaires pour le connecteur HAL Solr."""

import re
from dataclasses import dataclass
from typing import Any

from csc.contracts.models import ScholarlyWork
from csc.contracts.uuid_v7 import uuid7


@dataclass(frozen=True)
class ResearchStructure:
    """Structure de recherche ou institution académique référencée dans AuréHAL."""

    id: int
    acronym: str
    name: str
    description: str


KNOWN_STRUCTURES: dict[str, ResearchStructure] = {
    "INRAE": ResearchStructure(
        id=577435,
        acronym="INRAE",
        name="Institut National de Recherche pour l’Agriculture, l’Alimentation et l’Environnement",
        description="Recherche agronomique, alimentation, biodiversité, forêts et environnement",
    ),
    "IPP": ResearchStructure(
        id=266522,
        acronym="IPP",
        name="Institut des Politiques Publiques",
        description="Évaluation quantitative et analyse des politiques publiques (PSE/GENES)",
    ),
    "OFCE": ResearchStructure(
        id=250936,
        acronym="OFCE",
        name="Observatoire français des conjonctures économiques (Sciences Po)",
        description="Prévisions macroéconomiques, fiscalité et politiques environnementales",
    ),
    "CNRS-SHS": ResearchStructure(
        id=84039,
        acronym="INSHS-CNRS",
        name="Institut des Sciences Humaines et Sociales - CNRS Sciences humaines et sociales",
        description="Recherche en sciences humaines et sociales du CNRS",
    ),
    "LIEPP": ResearchStructure(
        id=218465,
        acronym="LIEPP",
        name="Laboratoire interdisciplinaire d'évaluation des politiques publiques (Sciences Po)",
        description="Évaluation interdisciplinaire des politiques publiques (méthodes mixtes)",
    ),
    "PSE": ResearchStructure(
        id=301309,
        acronym="PSE",
        name="Paris School of Economics - École d'économie de Paris",
        description="Recherche économique fondamentale et appliquée",
    ),
    "CEPII": ResearchStructure(
        id=110493,
        acronym="CEPII",
        name="Centre d'études prospectives et d'informations internationales",
        description="Économie internationale, commerce mondial, macroéconomie et finance",
    ),
    "CNRS": ResearchStructure(
        id=441569,
        acronym="CNRS",
        name="Centre National de la Recherche Scientifique",
        description="Organisme national de recherche pluridisciplinaire",
    ),
}


def resolve_struct_id(struct_input: str | int) -> int:
    """Résout un identifiant de structure à partir d'un entier ou d'un acronyme connu."""
    if isinstance(struct_input, int):
        return struct_input

    cleaned = str(struct_input).strip()
    if cleaned.isdigit():
        return int(cleaned)

    key = cleaned.upper()
    if key in KNOWN_STRUCTURES:
        return KNOWN_STRUCTURES[key].id

    # Recherche tolérante sur les clés avec tirets normalisés
    normalized_key = key.replace(" ", "-").replace("_", "-")
    for k, structure in KNOWN_STRUCTURES.items():
        if k.replace("_", "-") == normalized_key:
            return structure.id

    raise ValueError(
        f"Structure '{struct_input}' inconnue du référentiel. "
        f"Structures disponibles : {', '.join(KNOWN_STRUCTURES.keys())} ou passez un ID numérique."
    )


def normalize_doi(doi: str | list[str] | None) -> str | None:
    """Normalise un DOI en minuscules et supprime les préfixes d'URL usuels."""
    if not doi:
        return None

    raw: str
    if isinstance(doi, list):
        if not doi:
            return None
        raw = str(doi[0])
    else:
        raw = str(doi)

    d = raw.strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if d.lower().startswith(prefix):
            d = d[len(prefix) :].strip()

    d = d.rstrip("/")
    return d.lower() if d else None


def normalize_hal_id(hal_id: str | list[str] | None) -> str | None:
    """Normalise un identifiant HAL en extrayant le code sans URL ni version.

    Exemples :
    - 'halshs-00557065v1' -> 'halshs-00557065'
    - 'https://shs.hal.science/halshs-00557065v1' -> 'halshs-00557065'
    - 'hal-03707816' -> 'hal-03707816'
    """
    if not hal_id:
        return None

    raw: str
    if isinstance(hal_id, list):
        if not hal_id:
            return None
        raw = str(hal_id[0])
    else:
        raw = str(hal_id)

    cleaned = raw.strip()
    # Supprimer les éventuels préfixes URL
    if "/" in cleaned:
        cleaned = cleaned.rstrip("/").split("/")[-1]

    # Supprimer le suffixe de version (ex: v1, v2)
    cleaned = re.sub(r"v\d+$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() if cleaned else None


def escape_solr_phrase_term(term: str) -> str:
    """Échappe un terme pour une inclusion sécurisée dans une clause de proximité ou phrase Solr."""
    t = term.strip()
    # Échapper les barres obliques inverses
    t = t.replace("\\", "\\\\")
    # Échapper les guillemets doubles
    t = t.replace('"', '\\"')
    # Remplacer les retours à la ligne par des espaces
    t = re.sub(r"\s+", " ", t)
    return t


def build_proximity_query(term1: str, term2: str, distance: int) -> str:
    """Construit une clause de proximité Solr au format '"terme1 terme2"~N'.

    Exemple :
    build_proximity_query("taxe", "carbone", 3) -> '"taxe carbone"~3'
    """
    esc1 = escape_solr_phrase_term(term1)
    esc2 = escape_solr_phrase_term(term2)
    dist = max(0, int(distance))
    return f'"{esc1} {esc2}"~{dist}'


def parse_hal_doc(doc: dict[str, Any]) -> ScholarlyWork:
    """Convertit un document brut renvoyé par l'API Solr de HAL en ScholarlyWork."""
    # 1. Identifiant HAL
    hal_id = normalize_hal_id(doc.get("halId_s"))

    # 2. Titre
    title_raw = doc.get("title_s")
    title = ""
    if isinstance(title_raw, list):
        for item in title_raw:
            if item and str(item).strip():
                title = str(item).strip()
                break
    elif isinstance(title_raw, str):
        title = title_raw.strip()

    if not title:
        title = f"Document HAL {hal_id or 'sans titre'}"

    # 3. DOI normalisé
    doi = normalize_doi(doc.get("doiId_s"))

    # 4. Année
    year_raw = doc.get("producedDateY_i")
    year: int | None = None
    if year_raw is not None:
        try:
            val = int(year_raw)
            if 1800 <= val <= 2100:
                year = val
        except (ValueError, TypeError):
            year = None

    # 5. Abstract
    abstract_raw = doc.get("abstract_s")
    abstract: str | None = None
    if isinstance(abstract_raw, list):
        non_empty = [str(x).strip() for x in abstract_raw if str(x).strip()]
        if non_empty:
            abstract = "\n\n".join(non_empty)
    elif isinstance(abstract_raw, str) and abstract_raw.strip():
        abstract = abstract_raw.strip()

    # 6. Auteurs
    authors_raw = doc.get("authFullName_s")
    authors: list[str] = []
    if isinstance(authors_raw, list):
        for author in authors_raw:
            a_str = str(author).strip()
            if a_str and a_str not in authors:
                authors.append(a_str)
    elif isinstance(authors_raw, str) and authors_raw.strip():
        authors.append(authors_raw.strip())

    # 7. Structures & Venue
    struct_raw = doc.get("structName_s")
    structures: list[str] = []
    if isinstance(struct_raw, list):
        for st in struct_raw:
            s_str = str(st).strip()
            if s_str and s_str not in structures:
                structures.append(s_str)
    elif isinstance(struct_raw, str) and struct_raw.strip():
        structures.append(struct_raw.strip())

    journal_raw = doc.get("journalTitle_s")
    venue: str | None = None
    if isinstance(journal_raw, list):
        for j in journal_raw:
            j_str = str(j).strip()
            if j_str:
                venue = j_str
                break
    elif isinstance(journal_raw, str) and journal_raw.strip():
        venue = journal_raw.strip()

    doc_type = str(doc.get("docType_s") or "").strip().upper()
    if not venue:
        if doc_type == "THESE":
            venue = f"Thèse de doctorat ({structures[0]})" if structures else "Thèse de doctorat"
        elif doc_type == "REPORT":
            venue = structures[0] if structures else "Rapport de recherche"
        elif structures:
            venue = structures[0]

    # 8. URL d'accès
    uri_s = doc.get("uri_s")
    file_main = doc.get("fileMain_s")
    url: str | None = None
    if uri_s and isinstance(uri_s, str) and uri_s.strip():
        url = uri_s.strip()
    elif file_main and isinstance(file_main, str) and file_main.strip():
        url = file_main.strip()
    elif doi:
        url = f"https://doi.org/{doi}"
    elif hal_id:
        url = f"https://hal.science/{hal_id}"

    # 9. Détection des revues systématiques et méta-analyses
    title_lower = title.lower()
    abstract_lower = (abstract or "").lower()
    is_review = (
        "meta-analysis" in title_lower
        or "méta-analyse" in title_lower
        or "systematic review" in title_lower
        or "revue systématique" in title_lower
        or "meta-analysis" in abstract_lower
        or "systematic review" in abstract_lower
    )

    return ScholarlyWork(
        id=uuid7(),
        doi=doi,
        openalex_id=None,
        hal_id=hal_id,
        s2_id=None,
        title=title,
        year=year,
        venue=venue,
        cited_by_count=0,
        abstract=abstract,
        design=None,
        sms_level=None,
        is_systematic_review=is_review,
        authors=authors,
        url=url,
    )
