"""Modèles de données Pydantic v2 du projet Comparateur Science 2027."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from csc.contracts.enums import (
    CandidateStatus,
    ClaimType,
    ConsensusLevel,
    EvidenceDirection,
    FactualVerdict,
    LlmTier,
    RectificationStatus,
    ReviewDecision,
    ReviewStatus,
    SentenceKind,
    SourceKind,
    Theme,
    VotePosition,
)
from csc.contracts.uuid_v7 import uuid7


class Candidate(BaseModel):
    """Candidat ou candidate à l'élection présidentielle."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    slug: str = Field(min_length=1, description="Identifiant textuel d'URL (ex: claire-delacroix)")
    name: str = Field(min_length=1, description="Nom complet public")
    parties: list[str] = Field(default_factory=list, description="Partis de rattachement")
    parliamentary_group_id: str | None = Field(
        default=None, description="Groupe parlementaire lié le cas échéant"
    )
    status: CandidateStatus = Field(
        default=CandidateStatus.DECLARED, description="Statut de la candidature"
    )
    photo_url: str | None = Field(default=None, description="URL de la photo officielle")


class Party(BaseModel):
    """Parti politique."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(min_length=1, description="Identifiant ou sigle (ex: EELV, REN, RN)")
    name: str = Field(min_length=1, description="Nom complet du parti")
    short_name: str = Field(min_length=1, description="Sigle d'usage")
    color_hex: str | None = Field(
        default=None, description="Code couleur hexadécimal indicatif pour le site"
    )


class ParliamentaryGroup(BaseModel):
    """Groupe parlementaire (Assemblée nationale ou Sénat)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(min_length=1, description="Identifiant officiel (ex: EPR, RN, SOC)")
    name: str = Field(min_length=1, description="Nom complet du groupe")
    short_name: str = Field(min_length=1, description="Sigle d'usage")
    chamber: str = Field(
        default="assemblee", description="Chambre parlementaire ('assemblee' ou 'senat')"
    )


class SourceDocument(BaseModel):
    """Document source ingéré dans le système (programme, rapport, texte officiel)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    kind: SourceKind = Field(description="Nature du document source")
    url: str = Field(description="URL d'origine de récupération")
    sha256: str = Field(min_length=64, max_length=64, description="Empreinte SHA-256 du fichier")
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Horodatage de récupération",
    )
    licence: str = Field(
        default="Licence Ouverte 2.0", description="Licence d'utilisation du document"
    )
    robots_allowed: bool = Field(
        default=True, description="Respect des règles robots.txt lors de la collecte"
    )
    tdm_optout: bool = Field(
        default=False, description="Présence d'un opt-out Text and Data Mining (Art. L122-5-3 CPI)"
    )
    storage_path: str = Field(description="Chemin local du fichier sous var/pdf/")


class DocumentChunk(BaseModel):
    """Segment de texte extrait d'un document source avec son vecteur d'embedding."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    document_id: UUID = Field(description="Référence vers SourceDocument")
    page_start: int = Field(ge=1, description="Première page du segment")
    page_end: int = Field(ge=1, description="Dernière page du segment")
    text: str = Field(min_length=1, description="Contenu textuel du segment")
    embedding: list[float] | None = Field(
        default=None, description="Vecteur numérique (dim 1024 pour multilingual-e5-large)"
    )
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-large",
        description="Identifiant du modèle d'embedding utilisé",
    )


class Proposal(BaseModel):
    """Proposition politique extraite d'un programme électoral."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    candidate_id: UUID = Field(description="Référence vers Candidate")
    source_document_id: UUID = Field(description="Référence vers SourceDocument")
    page: int = Field(ge=1, description="Numéro de page dans le document source")
    exact_text: str = Field(min_length=1, description="Citation mot à mot de la proposition")
    theme: Theme = Field(description="Thématique principale rattachée")
    selected_by_rule: bool = Field(
        default=True, description="Indique si la proposition a été retenue par la règle de parité"
    )
    selection_reason: str | None = Field(
        default=None, description="Motif de sélection ou d'exclusion"
    )


class CausalTriple(BaseModel):
    """Triplet d'analyse causale (intervention, mécanisme théorisé, impact mesurable)."""

    model_config = ConfigDict(from_attributes=True)

    intervention: str = Field(min_length=1, description="Levier d'action proposé")
    mechanism: str = Field(min_length=1, description="Mécanisme ou chaîne d'impact postulée")
    outcome: str = Field(min_length=1, description="Résultat attendu mesurable")


class FactualStatement(BaseModel):
    """Détail pour une affirmation factuelle chiffrée ou descriptive."""

    model_config = ConfigDict(from_attributes=True)

    statement: str = Field(min_length=1, description="Énoncé du constat factuel")
    claimed_value: str | None = Field(default=None, description="Valeur avancée par le programme")
    reference_value: str | None = Field(
        default=None, description="Valeur de référence statistique/officielle"
    )
    source_reference: str | None = Field(
        default=None, description="Source statistique de référence (ex: Insee, DARES)"
    )


class Claim(BaseModel):
    """Affirmation individualisée prête pour l'évaluation scientifique."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    proposal_id: UUID = Field(description="Référence vers Proposal")
    type: ClaimType = Field(description="Type d'affirmation (normative, factual, causal)")
    normalized_text: str = Field(min_length=1, description="Texte normalisé débarrassé du lyrisme")
    causal_triple: CausalTriple | None = Field(default=None, description="Rempli si type == causal")
    factual_statement: FactualStatement | None = Field(
        default=None, description="Rempli si type == factual"
    )


class ScholarlyWork(BaseModel):
    """Publication scientifique évaluée par les pairs ou rapport institutionnel de référence."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    doi: str | None = Field(default=None, description="Digital Object Identifier normalisé")
    openalex_id: str | None = Field(default=None, description="Identifiant OpenAlex (ex: W123456)")
    hal_id: str | None = Field(default=None, description="Identifiant HAL (ex: hal-01234567)")
    s2_id: str | None = Field(default=None, description="Identifiant Semantic Scholar (S2)")
    title: str = Field(min_length=1, description="Titre complet de la publication")
    year: int | None = Field(default=None, ge=1800, le=2100, description="Année de parution")
    venue: str | None = Field(
        default=None, description="Revue, conférence ou institution émettrice"
    )
    cited_by_count: int = Field(default=0, ge=0, description="Nombre de citations recensées")
    abstract: str | None = Field(default=None, description="Résumé officiel de la publication")
    design: str | None = Field(
        default=None, description="Devis de recherche ou méthodologie (ex: RCT, DiD, RDD)"
    )
    sms_level: int | None = Field(
        default=None, ge=1, le=5, description="Niveau sur l'échelle Maryland SMS (1 à 5)"
    )
    is_systematic_review: bool = Field(
        default=False, description="Indique s'il s'agit d'une revue systématique ou méta-analyse"
    )
    authors: list[str] = Field(default_factory=list, description="Liste des auteurs principaux")
    url: str | None = Field(default=None, description="Lien d'accès ou de consultation")


class EvidenceQuery(BaseModel):
    """Requête de recherche documentaire scientifique (traçabilité publique)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    claim_id: UUID = Field(description="Référence vers Claim")
    source: str = Field(description="Source interrogée (openalex, hal, semantic_scholar...)")
    exact_query: str = Field(min_length=1, description="Texte exact ou filtres de la requête")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Paramètres d'API détaillés"
    )
    queried_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Date et heure de l'interrogation",
    )
    results_count: int = Field(
        default=0, ge=0, description="Nombre de résultats renvoyés par l'API"
    )


class EvidenceItem(BaseModel):
    """Élément de preuve individualisé extrait d'une publication ou d'un document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    claim_id: UUID = Field(description="Référence vers Claim")
    work_id: UUID | None = Field(
        default=None, description="Référence vers ScholarlyWork le cas échéant"
    )
    chunk_id: UUID | None = Field(
        default=None, description="Référence vers DocumentChunk le cas échéant"
    )
    relevance: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Score de pertinence thématique (0 à 1)"
    )
    direction: EvidenceDirection = Field(
        default=EvidenceDirection.SUPPORTS, description="Orientation de la preuve"
    )
    exact_quote: str = Field(min_length=1, description="Extrait textuel exact étayant l'évaluation")
    page: int | None = Field(
        default=None, ge=1, description="Numéro de page de l'extrait dans la publication"
    )


class Sentence(BaseModel):
    """Phrase d'une fiche d'évaluation avec obligations de citation vérifiées."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    text: str = Field(min_length=1, description="Texte de la phrase")
    kind: SentenceKind = Field(
        default=SentenceKind.STATEMENT, description="Nature de la phrase dans la fiche"
    )
    citations: list[UUID] = Field(
        default_factory=list,
        description="Identifiants d'EvidenceItem uniquement étayant cette phrase",
    )

    @model_validator(mode="after")
    def validate_citations_if_not_context(self) -> Self:
        """Vérifie qu'une phrase non contextuelle comporte au moins une citation."""
        if self.kind != SentenceKind.CONTEXT and len(self.citations) == 0:
            raise ValueError(
                "Une phrase de synthèse non contextuelle doit comporter au moins une "
                "citation d'un élément de preuve (EvidenceItem)."
            )
        return self


class AssessmentSections(BaseModel):
    """Sections structurées du corps de la fiche d'évaluation."""

    model_config = ConfigDict(from_attributes=True)

    diagnostic: str = Field(
        default="", description="Diagnostic de la situation et formulation du problème"
    )
    mechanism: str = Field(
        default="", description="Analyse du mécanisme causal ou vérification factuelle"
    )
    evidence: str = Field(
        default="", description="Synthèse des études empiriques et de leur robustesse"
    )
    blind_spots: str = Field(
        default="", description="Angles morts, effets rebonds et impacts redistributifs"
    )
    success_conditions: str = Field(
        default="", description="Conditions de réussite et sensibilité au contexte"
    )
    controversies: str = Field(default="", description="Controverses scientifiques non tranchées")


class Reviewer(BaseModel):
    """Chercheur ou expert relisant les fiches (données personnelles minimales RGPD)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    public_name: str = Field(min_length=1, description="Nom public affiché")
    orcid: str | None = Field(
        default=None, description="Identifiant ORCID (ex: 0000-0002-1825-0097)"
    )
    openalex_author_id: str | None = Field(default=None, description="Identifiant auteur OpenAlex")
    disciplines: list[str] = Field(
        default_factory=list, description="Champs disciplinaires d'expertise"
    )
    conflict_of_interest: str = Field(
        min_length=1, description="Déclaration publique de liens et d'intérêts"
    )


class Review(BaseModel):
    """Relecture humaine d'une version de fiche."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    assessment_id: UUID = Field(description="Référence vers Assessment")
    version: int = Field(default=1, ge=1, description="Numéro de version de fiche évaluée")
    reviewer_id: UUID = Field(description="Référence vers Reviewer")
    decision: ReviewDecision = Field(description="Décision finale de la relecture")
    comments: str = Field(min_length=1, description="Commentaires qualitatifs du relecteur")
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Horodatage de soumission",
    )
    duration_minutes: int | None = Field(
        default=None, ge=1, description="Temps passé en minutes pour audit de charge"
    )


class Assessment(BaseModel):
    """Fiche d'évaluation d'une affirmation politique au regard de la science."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    claim_id: UUID = Field(description="Référence vers Claim")
    version: int = Field(default=1, ge=1, description="Numéro de version séquentiel")
    status: ReviewStatus = Field(
        default=ReviewStatus.AI_DRAFT, description="Statut dans le workflow éditorial"
    )
    factual_verdict: FactualVerdict | None = Field(
        default=None, description="Verdict factuel si claim de type factual"
    )
    consensus_level: ConsensusLevel | None = Field(
        default=None, description="Niveau de consensus si claim de type causal"
    )
    evidence_direction: EvidenceDirection | None = Field(
        default=None, description="Orientation générale des preuves recensées"
    )
    sms_max: int | None = Field(
        default=None, ge=1, le=5, description="Score Maryland SMS le plus élevé parmi les preuves"
    )
    summary: str = Field(min_length=1, description="Résumé accessible de la fiche (<= 80 mots)")
    sections: AssessmentSections = Field(
        default_factory=AssessmentSections, description="Sections structurées du corps"
    )
    sentences: list[Sentence] = Field(
        default_factory=list, description="Liste ordonnée des phrases composant la fiche"
    )
    reviews: list[Review] = Field(
        default_factory=list, description="Historique des relectures humaines associées"
    )
    limitations: str | None = Field(
        default=None, description="Limites méthodologiques explicites de la fiche"
    )
    synthesiser_model: str | None = Field(
        default=None, description="Modèle LLM ayant rédigé le brouillon (ex: gemini-4-argon)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Date de création",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Dernière modification",
    )

    @model_validator(mode="after")
    def validate_approved_status_has_review(self) -> Self:
        """Vérifie qu'une fiche approuvée ou publiée a au moins une relecture approuvée."""
        if self.status in (ReviewStatus.APPROVED, ReviewStatus.PUBLISHED):
            has_approved_review = any(r.decision == ReviewDecision.APPROVED for r in self.reviews)
            if not has_approved_review:
                raise ValueError(
                    "Une fiche au statut 'approved' ou 'published' doit avoir au moins "
                    "une relecture approuvée par un relecteur humain (ReviewDecision.APPROVED)."
                )
        return self


class VerificationReport(BaseModel):
    """Rapport de vérification automatique déterministe et croisée d'une fiche."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    assessment_id: UUID = Field(description="Référence vers Assessment")
    version: int = Field(default=1, ge=1, description="Numéro de version de la fiche auditée")
    verifier_model: str = Field(
        description="Modèle LLM de vérification utilisé (doit être distinct du modèle rédacteur)"
    )
    same_provider: bool = Field(
        default=True,
        description="Indique si le vérificateur et le rédacteur partagent le même fournisseur",
    )
    controls: dict[str, Any] = Field(
        default_factory=dict,
        description="Résultats détaillés des contrôles (doi_resolves, numbers_match...)",
    )
    flags: list[str] = Field(
        default_factory=list, description="Liste des signaux d'alerte émis pour les relecteurs"
    )
    is_valid: bool = Field(default=True, description="Vrai si aucun contrôle bloquant n'a échoué")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Horodatage de génération du rapport",
    )


class ChangelogEntry(BaseModel):
    """Entrée d'historique de modification d'une fiche."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    assessment_id: UUID = Field(description="Référence vers Assessment")
    version: int = Field(default=1, ge=1, description="Version concernée")
    changed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Date de la modification",
    )
    reason: str = Field(min_length=1, description="Motif de la modification")
    author: str = Field(min_length=1, description="Auteur ou relecteur ayant effectué la révision")


class Scrutin(BaseModel):
    """Scrutin public parlementaire (Assemblée nationale ou Sénat)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(min_length=1, description="Identifiant officiel (ex: VTANR5L17V0001)")
    chamber: str = Field(default="assemblee", description="Chambre parlementaire")
    title: str = Field(min_length=1, description="Objet ou titre du scrutin")
    date: datetime = Field(description="Date du scrutin")
    solemn: bool = Field(
        default=False, description="Indique s'il s'agit d'un vote solennel sur l'ensemble du texte"
    )
    result: str = Field(description="Résultat officiel (ex: adopté, rejeté)")
    dossier_id: str | None = Field(
        default=None, description="Identifiant du dossier législatif lié"
    )


class Vote(BaseModel):
    """Vote individuel ou par groupe d'un parlementaire lors d'un scrutin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    scrutin_id: str = Field(description="Référence vers Scrutin")
    deputy_name: str = Field(min_length=1, description="Nom du parlementaire")
    group_id: str = Field(description="Groupe parlementaire lors du vote")
    position: VotePosition = Field(description="Position exprimée (pour, contre, abstention...)")


class Amendment(BaseModel):
    """Amendement parlementaire officiel."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(min_length=1, description="Identifiant officiel (ex: AMANR5L17...)")
    dossier_id: str = Field(description="Identifiant du dossier législatif")
    article: str = Field(description="Article visé par l'amendement")
    authors: list[str] = Field(default_factory=list, description="Auteurs de l'amendement")
    group_id: str | None = Field(default=None, description="Groupe politique principal porteur")
    expose_motifs: str = Field(description="Exposé des motifs de l'amendement")
    dispositif: str = Field(description="Dispositif juridique proposé")
    sort: str = Field(description="Sort de l'amendement (ex: adopté, rejeté, retiré)")
    scrutin_id: str | None = Field(
        default=None, description="Identifiant du scrutin public associé le cas échéant"
    )


class LlmCall(BaseModel):
    """Traçabilité immuable et audit de coût de tout appel LLM."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    prompt_id: str = Field(description="Nom canonique du prompt (ex: synthesis_causal)")
    prompt_version: str = Field(description="Version du gabarit de prompt")
    prompt_sha: str = Field(description="Empreinte SHA-256 du gabarit au moment de l'appel")
    provider: str = Field(default="gemini", description="Fournisseur d'IA (strictement gemini)")
    model: str = Field(description="Nom exact du modèle (ex: gemini-2.5-flash)")
    tier: LlmTier = Field(default=LlmTier.FREE, description="Palier tarifaire (free ou paid)")
    batch_job_id: str | None = Field(
        default=None, description="Identifiant du job de lot Batch API le cas échéant"
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="Paramètres d'inférence (température, top_p...)"
    )
    input_tokens: int = Field(default=0, ge=0, description="Tokens d'entrée consommés")
    cached_tokens: int = Field(default=0, ge=0, description="Tokens servis par le cache implicite")
    output_tokens: int = 0
    thinking_tokens: int = 0
    cost_usd: float = Field(default=0.0, ge=0.0, description="Coût réel calculé en dollars USD")
    latency_ms: int | None = Field(
        default=None, ge=0, description="Durée de l'appel en millisecondes"
    )
    raw_output: str | None = Field(
        default=None, description="Sortie brute textuelle retournée par le modèle"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Horodatage de l'appel",
    )


class RectificationRequest(BaseModel):
    """Demande citoyenne ou de chercheur signalant une erreur ou proposant une étude."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid7)
    assessment_id: UUID = Field(description="Référence vers Assessment")
    reason: str = Field(min_length=1, description="Description argumentée de l'erreur ou remarque")
    proposed_doi: str | None = Field(
        default=None, description="DOI d'une publication scientifique suggérée"
    )
    email: str | None = Field(
        default=None, description="E-mail facultatif de contact pour notification"
    )
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Date de réception",
    )
    imported_at: datetime | None = Field(
        default=None, description="Date de rapatriement dans la base locale"
    )
    status: RectificationStatus = Field(
        default=RectificationStatus.RECEIVED, description="Statut de traitement"
    )
    public_response: str | None = Field(
        default=None, description="Réponse publique motivée du conseil scientifique"
    )
