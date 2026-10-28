"""Schéma initial des contrats de données et activation de pgvector.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-28 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# Identifiants de révision utilisés par Alembic
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Activation de l'extension vector sur PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Table candidates
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parties", sa.JSON(), nullable=False),
        sa.Column("parliamentary_group_id", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="declared"),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidates_slug", "candidates", ["slug"], unique=True)
    op.create_index(
        "ix_candidates_parliamentary_group_id", "candidates", ["parliamentary_group_id"]
    )

    # 3. Table parties
    op.create_table(
        "parties",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=50), nullable=False),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Table parliamentary_groups
    op.create_table(
        "parliamentary_groups",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=50), nullable=False),
        sa.Column("chamber", sa.String(length=20), nullable=False, server_default="assemblee"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Table source_documents
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "licence",
            sa.String(length=100),
            nullable=False,
            server_default="Licence Ouverte 2.0",
        ),
        sa.Column("robots_allowed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tdm_optout", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_documents_sha256", "source_documents", ["sha256"], unique=True)

    # 6. Table document_chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column(
            "embedding_model",
            sa.String(length=100),
            nullable=False,
            server_default="intfloat/multilingual-e5-large",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # 7. Table proposals
    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("exact_text", sa.Text(), nullable=False),
        sa.Column("theme", sa.String(length=50), nullable=False),
        sa.Column("selected_by_rule", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("selection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], ["source_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposals_candidate_id", "proposals", ["candidate_id"])
    op.create_index("ix_proposals_source_document_id", "proposals", ["source_document_id"])
    op.create_index("ix_proposals_theme", "proposals", ["theme"])

    # 8. Table claims
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("causal_triple", sa.JSON(), nullable=True),
        sa.Column("factual_statement", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claims_proposal_id", "claims", ["proposal_id"])
    op.create_index("ix_claims_type", "claims", ["type"])

    # 9. Table scholarly_works
    op.create_table(
        "scholarly_works",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("openalex_id", sa.String(length=100), nullable=True),
        sa.Column("hal_id", sa.String(length=100), nullable=True),
        sa.Column("s2_id", sa.String(length=100), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("cited_by_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("design", sa.String(length=100), nullable=True),
        sa.Column("sms_level", sa.Integer(), nullable=True),
        sa.Column("is_systematic_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scholarly_works_doi", "scholarly_works", ["doi"], unique=True)
    op.create_index("ix_scholarly_works_openalex_id", "scholarly_works", ["openalex_id"])
    op.create_index("ix_scholarly_works_hal_id", "scholarly_works", ["hal_id"])
    op.create_index("ix_scholarly_works_s2_id", "scholarly_works", ["s2_id"])
    op.create_index("ix_scholarly_works_year", "scholarly_works", ["year"])

    # 10. Table evidence_queries
    op.create_table(
        "evidence_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("exact_query", sa.Text(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("queried_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_queries_claim_id", "evidence_queries", ["claim_id"])

    # 11. Table evidence_items
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("work_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("relevance", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("direction", sa.String(length=20), nullable=False, server_default="supports"),
        sa.Column("exact_quote", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_id"], ["scholarly_works.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_items_claim_id", "evidence_items", ["claim_id"])
    op.create_index("ix_evidence_items_work_id", "evidence_items", ["work_id"])
    op.create_index("ix_evidence_items_chunk_id", "evidence_items", ["chunk_id"])

    # 12. Table assessments
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ai_draft"),
        sa.Column("factual_verdict", sa.String(length=30), nullable=True),
        sa.Column("consensus_level", sa.String(length=30), nullable=True),
        sa.Column("evidence_direction", sa.String(length=20), nullable=True),
        sa.Column("sms_max", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("sentences", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("synthesiser_model", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessments_claim_id", "assessments", ["claim_id"])
    op.create_index("ix_assessments_status", "assessments", ["status"])

    # 13. Table reviewers
    op.create_table(
        "reviewers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_name", sa.String(length=255), nullable=False),
        sa.Column("orcid", sa.String(length=50), nullable=True),
        sa.Column("openalex_author_id", sa.String(length=100), nullable=True),
        sa.Column("disciplines", sa.JSON(), nullable=False),
        sa.Column("conflict_of_interest", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviewers_orcid", "reviewers", ["orcid"])
    op.create_index("ix_reviewers_openalex_author_id", "reviewers", ["openalex_author_id"])

    # 14. Table reviews
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("comments", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["reviewers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_assessment_id", "reviews", ["assessment_id"])
    op.create_index("ix_reviews_reviewer_id", "reviews", ["reviewer_id"])

    # 15. Table verification_reports
    op.create_table(
        "verification_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("verifier_model", sa.String(length=100), nullable=False),
        sa.Column("same_provider", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("controls", sa.JSON(), nullable=False),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_verification_reports_assessment_id", "verification_reports", ["assessment_id"]
    )

    # 16. Table changelog_entries
    op.create_table(
        "changelog_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_changelog_entries_assessment_id", "changelog_entries", ["assessment_id"])

    # 17. Table scrutins
    op.create_table(
        "scrutins",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("chamber", sa.String(length=20), nullable=False, server_default="assemblee"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("solemn", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("result", sa.String(length=50), nullable=False),
        sa.Column("dossier_id", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scrutins_dossier_id", "scrutins", ["dossier_id"])

    # 18. Table votes
    op.create_table(
        "votes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scrutin_id", sa.String(length=100), nullable=False),
        sa.Column("deputy_name", sa.String(length=255), nullable=False),
        sa.Column("group_id", sa.String(length=50), nullable=False),
        sa.Column("position", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["scrutin_id"], ["scrutins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_votes_scrutin_id", "votes", ["scrutin_id"])
    op.create_index("ix_votes_group_id", "votes", ["group_id"])

    # 19. Table amendments
    op.create_table(
        "amendments",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("dossier_id", sa.String(length=100), nullable=False),
        sa.Column("article", sa.String(length=100), nullable=False),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("group_id", sa.String(length=50), nullable=True),
        sa.Column("expose_motifs", sa.Text(), nullable=False),
        sa.Column("dispositif", sa.Text(), nullable=False),
        sa.Column("sort", sa.String(length=50), nullable=False),
        sa.Column("scrutin_id", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["scrutin_id"], ["scrutins.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_amendments_dossier_id", "amendments", ["dossier_id"])
    op.create_index("ix_amendments_group_id", "amendments", ["group_id"])
    op.create_index("ix_amendments_scrutin_id", "amendments", ["scrutin_id"])

    # 20. Table llm_calls
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prompt_id", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("prompt_sha", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="gemini"),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False, server_default="paid"),
        sa.Column("batch_job_id", sa.String(length=100), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("thinking_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_calls_prompt_id", "llm_calls", ["prompt_id"])
    op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"])

    # 21. Table rectification_requests
    op.create_table(
        "rectification_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("proposed_doi", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="received"),
        sa.Column("public_response", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assessment_id"], ["assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rectification_requests_assessment_id",
        "rectification_requests",
        ["assessment_id"],
    )


def downgrade() -> None:
    op.drop_table("rectification_requests")
    op.drop_table("llm_calls")
    op.drop_table("amendments")
    op.drop_table("votes")
    op.drop_table("scrutins")
    op.drop_table("changelog_entries")
    op.drop_table("verification_reports")
    op.drop_table("reviews")
    op.drop_table("reviewers")
    op.drop_table("assessments")
    op.drop_table("evidence_items")
    op.drop_table("evidence_queries")
    op.drop_table("scholarly_works")
    op.drop_table("claims")
    op.drop_table("proposals")
    op.drop_table("document_chunks")
    op.drop_table("source_documents")
    op.drop_table("parliamentary_groups")
    op.drop_table("parties")
    op.drop_table("candidates")
