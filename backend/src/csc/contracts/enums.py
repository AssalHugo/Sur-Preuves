"""Énumérations métier du projet Comparateur Science 2027."""

from enum import IntEnum, StrEnum


class ClaimType(StrEnum):
    """Typologie des affirmations extraites des programmes."""

    NORMATIVE = "normative"
    FACTUAL = "factual"
    CAUSAL = "causal"


class FactualVerdict(StrEnum):
    """Verdict factuel pour les affirmations de type factual."""

    ACCURATE = "accurate"
    APPROXIMATE = "approximate"
    MISLEADING = "misleading"
    INACCURATE = "inaccurate"
    UNVERIFIABLE = "unverifiable"


class EvidenceDirection(StrEnum):
    """Direction dans laquelle pointe la preuve scientifique par rapport à l'affirmation."""

    SUPPORTS = "supports"
    MIXED = "mixed"
    CONTRADICTS = "contradicts"
    INCONCLUSIVE = "inconclusive"


class ConsensusLevel(StrEnum):
    """Niveau de consensus scientifique pour les affirmations de type causal."""

    STRONG = "strong"
    EMERGING = "emerging"
    CONTESTED = "contested"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOVEL_NO_EX_POST = "novel_no_ex_post"


class SmsLevel(IntEnum):
    """Échelle de Maryland Scientific Methods Scale (SMS) de 1 à 5."""

    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5


class Theme(StrEnum):
    """Taxonomie d'environ 15 thèmes des politiques publiques."""

    ECONOMIE_EMPLOI = "economie-emploi"
    FISCALITE = "fiscalite"
    RETRAITES = "retraites"
    SANTE = "sante"
    EDUCATION = "education"
    ENERGIE = "energie"
    CLIMAT = "climat"
    AGRICULTURE = "agriculture"
    LOGEMENT = "logement"
    SECURITE_JUSTICE = "securite-justice"
    IMMIGRATION = "immigration"
    TRANSPORT = "transport"
    NUMERIQUE = "numerique"
    INSTITUTIONS = "institutions"
    EUROPE_INTERNATIONAL = "europe-international"


class ReviewStatus(StrEnum):
    """Cycle de vie d'une fiche d'évaluation."""

    AI_DRAFT = "ai_draft"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class SourceKind(StrEnum):
    """Nature du document source ingéré ou référencé."""

    PROGRAMME = "programme"
    PROFESSION_DE_FOI = "profession_de_foi"
    AMENDMENT = "amendment"
    VOTE = "vote"
    SCHOLARLY_WORK = "scholarly_work"
    INSTITUTIONAL_REPORT = "institutional_report"


class CandidateStatus(StrEnum):
    """Statut de déclaration du candidat à l'élection présidentielle."""

    DECLARED = "declared"
    OFFICIAL = "official"


class SentenceKind(StrEnum):
    """Catégorie fonctionnelle d'une phrase de fiche de synthèse."""

    CONTEXT = "context"
    STATEMENT = "statement"
    MECHANISM = "mechanism"
    EVIDENCE = "evidence"
    BLIND_SPOTS = "blind_spots"
    CONDITIONS = "conditions"
    CONTROVERSY = "controversy"
    LIMITATION = "limitation"


class ReviewDecision(StrEnum):
    """Décision prise par un relecteur humain sur une version de fiche."""

    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class CitationSupportVerdict(StrEnum):
    """Évaluation du soutien d'une phrase par les extraits cités."""

    SUPPORTED = "supported"
    PARTIALLY = "partially"
    NOT_SUPPORTED = "not_supported"


class LlmTier(StrEnum):
    """Niveau de tarification de l'appel LLM."""

    PAID = "paid"
    FREE = "free"


class RectificationStatus(StrEnum):
    """Statut d'une demande publique de rectification ou proposition d'étude."""

    RECEIVED = "received"
    IMPORTED = "imported"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class VotePosition(StrEnum):
    """Position lors d'un vote parlementaire."""

    POUR = "pour"
    CONTRE = "contre"
    ABSTENTION = "abstention"
    NON_VOTANT = "non_votant"
