"""Modèles relationnels SQLAlchemy 2.0 pour PostgreSQL avec pgvector."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from csc.contracts.uuid_v7 import uuid7


class Base(DeclarativeBase):
    """Classe de base déclarative pour tous les modèles ORM."""

    pass


class CandidateModel(Base):
    """Table des candidats et candidates."""

    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parties: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    parliamentary_group_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="declared")
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    proposals: Mapped[list[ProposalModel]] = relationship(
        "ProposalModel", back_populates="candidate", cascade="all, delete-orphan"
    )


class PartyModel(Base):
    """Table des partis politiques."""

    __tablename__ = "parties"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)


class ParliamentaryGroupModel(Base):
    """Table des groupes parlementaires."""

    __tablename__ = "parliamentary_groups"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    chamber: Mapped[str] = mapped_column(String(20), nullable=False, default="assemblee")


class SourceDocumentModel(Base):
    """Table des documents sources collectés et audités."""

    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    licence: Mapped[str] = mapped_column(String(100), nullable=False, default="Licence Ouverte 2.0")
    robots_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tdm_optout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    chunks: Mapped[list[DocumentChunkModel]] = relationship(
        "DocumentChunkModel", back_populates="document", cascade="all, delete-orphan"
    )
    proposals: Mapped[list[ProposalModel]] = relationship(
        "ProposalModel", back_populates="source_document", cascade="all, delete-orphan"
    )


class DocumentChunkModel(Base):
    """Table des segments de documents avec vecteurs d'embeddings pgvector."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    embedding_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="intfloat/multilingual-e5-large"
    )

    document: Mapped[SourceDocumentModel] = relationship(
        "SourceDocumentModel", back_populates="chunks"
    )


class ProposalModel(Base):
    """Table des propositions de programme retenues."""

    __tablename__ = "proposals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    exact_text: Mapped[str] = mapped_column(Text, nullable=False)
    theme: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    selected_by_rule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    selection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate: Mapped[CandidateModel] = relationship("CandidateModel", back_populates="proposals")
    source_document: Mapped[SourceDocumentModel] = relationship(
        "SourceDocumentModel", back_populates="proposals"
    )
    claims: Mapped[list[ClaimModel]] = relationship(
        "ClaimModel", back_populates="proposal", cascade="all, delete-orphan"
    )


class ClaimModel(Base):
    """Table des affirmations factuelles et causales."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    causal_triple: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    factual_statement: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    proposal: Mapped[ProposalModel] = relationship("ProposalModel", back_populates="claims")
    queries: Mapped[list[EvidenceQueryModel]] = relationship(
        "EvidenceQueryModel", back_populates="claim", cascade="all, delete-orphan"
    )
    evidence_items: Mapped[list[EvidenceItemModel]] = relationship(
        "EvidenceItemModel", back_populates="claim", cascade="all, delete-orphan"
    )
    assessments: Mapped[list[AssessmentModel]] = relationship(
        "AssessmentModel", back_populates="claim", cascade="all, delete-orphan"
    )


class ScholarlyWorkModel(Base):
    """Table des publications scientifiques et rapports institutionnels."""

    __tablename__ = "scholarly_works"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    openalex_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    hal_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    s2_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cited_by_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    design: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sms_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_systematic_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence_items: Mapped[list[EvidenceItemModel]] = relationship(
        "EvidenceItemModel", back_populates="work"
    )


class EvidenceQueryModel(Base):
    """Table de traçabilité des requêtes documentaires."""

    __tablename__ = "evidence_queries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    exact_query: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    queried_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    results_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    claim: Mapped[ClaimModel] = relationship("ClaimModel", back_populates="queries")


class EvidenceItemModel(Base):
    """Table des extraits de preuves rattachés aux affirmations."""

    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    work_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("scholarly_works.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    relevance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="supports")
    exact_quote: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    claim: Mapped[ClaimModel] = relationship("ClaimModel", back_populates="evidence_items")
    work: Mapped[ScholarlyWorkModel | None] = relationship(
        "ScholarlyWorkModel", back_populates="evidence_items"
    )


class AssessmentModel(Base):
    """Table des fiches d'évaluation complètes."""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ai_draft", index=True)
    factual_verdict: Mapped[str | None] = mapped_column(String(30), nullable=True)
    consensus_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    evidence_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sms_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    sentences: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    synthesiser_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    claim: Mapped[ClaimModel] = relationship("ClaimModel", back_populates="assessments")
    reviews: Mapped[list[ReviewModel]] = relationship(
        "ReviewModel", back_populates="assessment", cascade="all, delete-orphan"
    )
    verification_reports: Mapped[list[VerificationReportModel]] = relationship(
        "VerificationReportModel",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    changelog: Mapped[list[ChangelogEntryModel]] = relationship(
        "ChangelogEntryModel",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    rectification_requests: Mapped[list[RectificationRequestModel]] = relationship(
        "RectificationRequestModel",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )


class ReviewerModel(Base):
    """Table des relecteurs scientifiques (profils publics et conformité RGPD)."""

    __tablename__ = "reviewers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    public_name: Mapped[str] = mapped_column(String(255), nullable=False)
    orcid: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    openalex_author_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    disciplines: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    conflict_of_interest: Mapped[str] = mapped_column(Text, nullable=False)

    reviews: Mapped[list[ReviewModel]] = relationship("ReviewModel", back_populates="reviewer")


class ReviewModel(Base):
    """Table des relectures humaines."""

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("reviewers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    assessment: Mapped[AssessmentModel] = relationship("AssessmentModel", back_populates="reviews")
    reviewer: Mapped[ReviewerModel] = relationship("ReviewerModel", back_populates="reviews")


class VerificationReportModel(Base):
    """Table des rapports d'audit déterministe et croisé."""

    __tablename__ = "verification_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    verifier_model: Mapped[str] = mapped_column(String(100), nullable=False)
    same_provider: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    controls: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    assessment: Mapped[AssessmentModel] = relationship(
        "AssessmentModel", back_populates="verification_reports"
    )


class ChangelogEntryModel(Base):
    """Table de l'historique des modifications de fiches."""

    __tablename__ = "changelog_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)

    assessment: Mapped[AssessmentModel] = relationship(
        "AssessmentModel", back_populates="changelog"
    )


class ScrutinModel(Base):
    """Table des scrutins publics de l'Assemblée nationale ou du Sénat."""

    __tablename__ = "scrutins"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    chamber: Mapped[str] = mapped_column(String(20), nullable=False, default="assemblee")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    solemn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    dossier_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    votes: Mapped[list[VoteModel]] = relationship(
        "VoteModel", back_populates="scrutin", cascade="all, delete-orphan"
    )


class VoteModel(Base):
    """Table des votes parlementaires individuels."""

    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    scrutin_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("scrutins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deputy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(20), nullable=False)

    scrutin: Mapped[ScrutinModel] = relationship("ScrutinModel", back_populates="votes")


class AmendmentModel(Base):
    """Table des amendements parlementaires."""

    __tablename__ = "amendments"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    dossier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    article: Mapped[str] = mapped_column(String(100), nullable=False)
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    group_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    expose_motifs: Mapped[str] = mapped_column(Text, nullable=False)
    dispositif: Mapped[str] = mapped_column(Text, nullable=False)
    sort: Mapped[str] = mapped_column(String(50), nullable=False)
    scrutin_id: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey("scrutins.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class LlmCallModel(Base):
    """Table d'enregistrement et de traçabilité des appels LLM."""

    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    prompt_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="paid")
    batch_job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thinking_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )


class RectificationRequestModel(Base):
    """Table des signalements et demandes citoyennes de rectification."""

    __tablename__ = "rectification_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    public_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[AssessmentModel] = relationship(
        "AssessmentModel", back_populates="rectification_requests"
    )
