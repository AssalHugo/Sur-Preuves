"""Contrat de publication du bundle JSON pour le site statique (L15 / L16)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from csc.contracts.enums import ReviewStatus, Theme
from csc.contracts.models import (
    Assessment,
    Candidate,
    ChangelogEntry,
    EvidenceQuery,
    ScholarlyWork,
)


class ThemeMetadata(BaseModel):
    """Métadonnées éditoriales décrivant un thème politique."""

    model_config = ConfigDict(from_attributes=True)

    id: Theme = Field(description="Identifiant canonique du thème")
    label: str = Field(min_length=1, description="Libellé éditorial en français")
    description: str = Field(min_length=1, description="Périmètre thématique et enjeux")


THEMES_CATALOG: list[ThemeMetadata] = [
    ThemeMetadata(
        id=Theme.ECONOMIE_EMPLOI,
        label="Économie & Emploi",
        description=(
            "Marché du travail, emploi, salaires, compétitivité des entreprises et "
            "réindustrialisation."
        ),
    ),
    ThemeMetadata(
        id=Theme.FISCALITE,
        label="Fiscalité & Finances publiques",
        description=(
            "Impôts, prélèvements obligatoires, dette souveraine et redistribution fiscale."
        ),
    ),
    ThemeMetadata(
        id=Theme.RETRAITES,
        label="Retraites",
        description=(
            "Équilibre des régimes, âge de départ, carrières longues et pénibilité au travail."
        ),
    ),
    ThemeMetadata(
        id=Theme.SANTE,
        label="Santé",
        description=(
            "Hôpital public, accès aux soins, déserts médicaux, santé mentale et prévention."
        ),
    ),
    ThemeMetadata(
        id=Theme.EDUCATION,
        label="Éducation & Recherche",
        description=(
            "Système scolaire primaire et secondaire, enseignement supérieur et investissement "
            "dans la recherche."
        ),
    ),
    ThemeMetadata(
        id=Theme.ENERGIE,
        label="Énergie",
        description="Mix électrique, nucléaire, énergies renouvelables et sobriété énergétique.",
    ),
    ThemeMetadata(
        id=Theme.CLIMAT,
        label="Climat & Biodiversité",
        description=(
            "Trajectoire de décarbonation, atténuation, adaptation au changement climatique et "
            "préservation des écosystèmes."
        ),
    ),
    ThemeMetadata(
        id=Theme.AGRICULTURE,
        label="Agriculture & Alimentation",
        description=(
            "Revenus agricoles, souveraineté alimentaire, pesticides et transition agroécologique."
        ),
    ),
    ThemeMetadata(
        id=Theme.LOGEMENT,
        label="Logement",
        description=(
            "Accès au logement, rénovation thermique, encadrement des loyers et construction neuve."
        ),
    ),
    ThemeMetadata(
        id=Theme.SECURITE_JUSTICE,
        label="Sécurité & Justice",
        description=(
            "Moyens de la justice, surpopulation carcérale, maintien de l'ordre et prévention de "
            "la délinquance."
        ),
    ),
    ThemeMetadata(
        id=Theme.IMMIGRATION,
        label="Immigration & Asile",
        description="Politique migratoire, droit d'asile, intégration et régulation des flux.",
    ),
    ThemeMetadata(
        id=Theme.TRANSPORT,
        label="Transports & Mobilités",
        description=(
            "Réseau ferroviaire, mobilités actives, véhicule électrique et infrastructures "
            "autoroutières."
        ),
    ),
    ThemeMetadata(
        id=Theme.NUMERIQUE,
        label="Numérique & Technologies",
        description=(
            "Intelligence artificielle, régulation des plateformes numériques, souveraineté "
            "logicielle et cybersécurité."
        ),
    ),
    ThemeMetadata(
        id=Theme.INSTITUTIONS,
        label="Institutions & Vie démocratique",
        description=(
            "Réforme constitutionnelle, proportionnelle, référendum d'initiative citoyenne et "
            "fonctionnement parlementaire."
        ),
    ),
    ThemeMetadata(
        id=Theme.EUROPE_INTERNATIONAL,
        label="Europe & International",
        description=(
            "Politique européenne, souveraineté diplomatique, traités de libre-échange et défense."
        ),
    ),
]


class AiDisclosure(BaseModel):
    """Mentions obligatoires sur l'usage de l'intelligence artificielle (Art. 50 AI Act)."""

    model_config = ConfigDict(from_attributes=True)

    ai_assisted: bool = Field(
        default=True,
        description="Indicateur d'assistance par intelligence artificielle",
    )
    statement: str = Field(
        default=(
            "Brouillons rédigés avec l'assistance d'un modèle d'IA (Gemini), systématiquement "
            "soumis à des contrôles déterministes et validés par des relecteurs humains qualifiés "
            "sous la responsabilité du conseil scientifique de Comparateur Science 2027."
        ),
        description="Mention publique d'information éditoriale",
    )
    digital_source_type: str = Field(
        default="trainedAlgorithmicMedia",
        description="Métadonnée IPTC conforme à la provenance algorithmique",
    )
    methodology_url: str = Field(
        default="/methodologie/",
        description="URL locale vers la méthodologie détaillée et les protocoles de vérification",
    )
    supervision_notice: str = Field(
        default=(
            "Aucune évaluation, notation ni verdict n'est publié sans validation explicite par un "
            "relecteur scientifique humain. Aucun profilage ni traitement automatisé de données "
            "visiteur n'est opéré."
        ),
        description="Garantie de conformité éthique et RGPD",
    )


class PublicationBundle(BaseModel):
    """Bundle JSON versionné consommé par le générateur de site statique Astro (L15)."""

    model_config = ConfigDict(from_attributes=True)

    schema_version: str = Field(
        default="1.0.0",
        description="Version du schéma du bundle de publication (Semantic Versioning)",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Horodatage ISO 8601 de génération du bundle",
    )
    candidates: list[Candidate] = Field(
        default_factory=list,
        description="Candidats officiels ou déclarés retenus dans le comparateur",
    )
    themes: list[ThemeMetadata] = Field(
        default_factory=lambda: list(THEMES_CATALOG),
        description="Taxonomie complète des thématiques évaluées",
    )
    assessments: list[Assessment] = Field(
        default_factory=list,
        description="Fiches d'évaluation (statut approuvé ou publié uniquement en production)",
    )
    works: list[ScholarlyWork] = Field(
        default_factory=list,
        description="Publications scientifiques mobilisées dans les fiches",
    )
    queries: list[EvidenceQuery] = Field(
        default_factory=list,
        description="Traçabilité publique des requêtes documentaires exécutées",
    )
    changelog: list[ChangelogEntry] = Field(
        default_factory=list,
        description="Historique public des révisions et rectifications",
    )
    ai_disclosure: AiDisclosure = Field(
        default_factory=AiDisclosure,
        description="Mentions de transparence et conformité réglementaire",
    )

    @model_validator(mode="after")
    def validate_only_approved_assessments(self) -> Self:
        """S'assure que le bundle ne contient que des fiches approuvées ou publiées."""
        unapproved = [
            a.id
            for a in self.assessments
            if a.status not in (ReviewStatus.APPROVED, ReviewStatus.PUBLISHED)
        ]
        if unapproved:
            raise ValueError(
                f"Le bundle de publication ne peut contenir que des fiches au statut 'approved' "
                f"ou 'published'. Fiches non conformes détectées : {unapproved}"
            )
        return self


def generate_bundle_schema() -> dict[str, Any]:
    """Génère le JSON Schema standard pour le bundle de publication."""
    schema = PublicationBundle.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


def export_bundle_schema(target_path: Path | str) -> Path:
    """Exporte le schéma JSON du bundle vers le chemin de fichier indiqué."""
    dest = Path(target_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    schema = generate_bundle_schema()
    dest.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest
