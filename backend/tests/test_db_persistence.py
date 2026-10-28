"""Tests d'intégration de persistance SQLAlchemy et pgvector."""

from sqlalchemy import select

from csc.contracts.uuid_v7 import uuid7
from csc.db.models import (
    AssessmentModel,
    CandidateModel,
    DocumentChunkModel,
    ProposalModel,
    ReviewerModel,
    ReviewModel,
    SourceDocumentModel,
)
from csc.db.session import get_session


def test_db_persistence_candidate_and_proposal() -> None:
    c_id = uuid7()
    doc_id = uuid7()
    p_id = uuid7()

    with get_session() as session:
        # Nettoyage si existant
        session.query(CandidateModel).filter_by(slug="test-persistence-cand").delete()

        candidate = CandidateModel(
            id=c_id,
            slug="test-persistence-cand",
            name="Candidat Persistance",
            parties=["PES"],
            status="declared",
        )
        session.add(candidate)

        doc = SourceDocumentModel(
            id=doc_id,
            kind="programme",
            url="https://example.org/test.pdf",
            sha256="f" * 64,
            storage_path="var/pdf/test.pdf",
        )
        session.add(doc)

        chunk = DocumentChunkModel(
            id=uuid7(),
            document_id=doc_id,
            page_start=1,
            page_end=1,
            text="Texte de segment",
            embedding=[0.05] * 1024,
        )
        session.add(chunk)

        proposal = ProposalModel(
            id=p_id,
            candidate_id=c_id,
            source_document_id=doc_id,
            page=2,
            exact_text="Proposition de test",
            theme="climat",
        )
        session.add(proposal)

    # Lecture dans une nouvelle session
    with get_session() as session:
        stmt = select(CandidateModel).where(CandidateModel.slug == "test-persistence-cand")
        res = session.scalars(stmt).one()
        assert res.name == "Candidat Persistance"
        assert len(res.proposals) == 1
        assert res.proposals[0].theme == "climat"

        # Nettoyage
        session.delete(res)
        doc_stmt = select(SourceDocumentModel).where(SourceDocumentModel.id == doc_id)
        doc_res = session.scalars(doc_stmt).one()
        session.delete(doc_res)


def test_db_persistence_assessment_and_reviews() -> None:
    ass_id = uuid7()
    rev_id = uuid7()
    c_id = uuid7()
    doc_id = uuid7()
    p_id = uuid7()
    claim_id = uuid7()

    with get_session() as session:
        candidate = CandidateModel(
            id=c_id,
            slug="cand-ass-test",
            name="Candidat Fiche",
            parties=["PES"],
            status="declared",
        )
        doc = SourceDocumentModel(
            id=doc_id,
            kind="programme",
            url="https://example.org/test_doc.pdf",
            sha256="d" * 64,
            storage_path="var/pdf/test_doc.pdf",
        )
        proposal = ProposalModel(
            id=p_id,
            candidate_id=c_id,
            source_document_id=doc_id,
            page=1,
            exact_text="Texte proposition",
            theme="sante",
        )
        session.add_all([candidate, doc, proposal])
        session.flush()

        from csc.db.models import ClaimModel

        claim = ClaimModel(
            id=claim_id,
            proposal_id=p_id,
            type="causal",
            normalized_text="Affirmation test",
        )
        session.add(claim)

        reviewer = ReviewerModel(
            id=rev_id,
            public_name="Dr. Testeur",
            orcid="0000-0001-2345-6789",
            disciplines=["Santé"],
            conflict_of_interest="Aucun conflit.",
        )
        session.add(reviewer)

        assessment = AssessmentModel(
            id=ass_id,
            claim_id=claim_id,
            version=1,
            status="approved",
            consensus_level="strong",
            summary="Résumé validé.",
            sections={"diagnostic": "Diag"},
            sentences=[
                {"id": str(uuid7()), "text": "Phrase 1", "kind": "statement", "citations": []}
            ],
        )
        session.add(assessment)

        review = ReviewModel(
            id=uuid7(),
            assessment_id=ass_id,
            version=1,
            reviewer_id=rev_id,
            decision="approved",
            comments="Validation complète",
            duration_minutes=25,
        )
        session.add(review)

    with get_session() as session:
        stmt = select(AssessmentModel).where(AssessmentModel.id == ass_id)
        ass = session.scalars(stmt).one()
        assert ass.status == "approved"
        assert len(ass.reviews) == 1
        assert ass.reviews[0].decision == "approved"

        # Suppression en cascade
        cand_stmt = select(CandidateModel).where(CandidateModel.id == c_id)
        cand_res = session.scalars(cand_stmt).one()
        session.delete(cand_res)

        doc_stmt = select(SourceDocumentModel).where(SourceDocumentModel.id == doc_id)
        session.delete(session.scalars(doc_stmt).one())

        rev_stmt = select(ReviewerModel).where(ReviewerModel.id == rev_id)
        session.delete(session.scalars(rev_stmt).one())
