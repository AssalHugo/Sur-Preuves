"""Tests de conversion bidirectionnelle Pydantic <-> SQLAlchemy ORM."""

from datetime import UTC, datetime

from csc.contracts.enums import (
    CandidateStatus,
    ClaimType,
    ConsensusLevel,
    EvidenceDirection,
    LlmTier,
    RectificationStatus,
    ReviewDecision,
    ReviewStatus,
    SentenceKind,
    SourceKind,
    Theme,
    VotePosition,
)
from csc.contracts.models import (
    Amendment,
    Assessment,
    AssessmentSections,
    Candidate,
    CausalTriple,
    ChangelogEntry,
    Claim,
    DocumentChunk,
    EvidenceItem,
    EvidenceQuery,
    FactualStatement,
    LlmCall,
    ParliamentaryGroup,
    Party,
    Proposal,
    RectificationRequest,
    Review,
    Reviewer,
    ScholarlyWork,
    Scrutin,
    Sentence,
    SourceDocument,
    VerificationReport,
    Vote,
)
from csc.contracts.uuid_v7 import uuid7
from csc.db.conversion import (
    amendment_from_orm,
    amendment_to_orm,
    assessment_from_orm,
    assessment_to_orm,
    candidate_from_orm,
    candidate_to_orm,
    changelog_entry_from_orm,
    changelog_entry_to_orm,
    claim_from_orm,
    claim_to_orm,
    document_chunk_from_orm,
    document_chunk_to_orm,
    evidence_item_from_orm,
    evidence_item_to_orm,
    evidence_query_from_orm,
    evidence_query_to_orm,
    llm_call_from_orm,
    llm_call_to_orm,
    parliamentary_group_from_orm,
    parliamentary_group_to_orm,
    party_from_orm,
    party_to_orm,
    proposal_from_orm,
    proposal_to_orm,
    rectification_request_from_orm,
    rectification_request_to_orm,
    review_from_orm,
    review_to_orm,
    reviewer_from_orm,
    reviewer_to_orm,
    scholarly_work_from_orm,
    scholarly_work_to_orm,
    scrutin_from_orm,
    scrutin_to_orm,
    source_document_from_orm,
    source_document_to_orm,
    verification_report_from_orm,
    verification_report_to_orm,
    vote_from_orm,
    vote_to_orm,
)


def test_candidate_conversion_roundtrip() -> None:
    original = Candidate(
        slug="claire-delacroix",
        name="Claire Delacroix",
        parties=["PES"],
        parliamentary_group_id="ECO-SOL",
        status=CandidateStatus.DECLARED,
        photo_url="/images/cd.jpg",
    )
    orm = candidate_to_orm(original)
    recovered = candidate_from_orm(orm)
    assert recovered == original


def test_party_and_group_roundtrip() -> None:
    party = Party(id="PES", name="Parti Écologique", short_name="Écolo", color_hex="#10b981")
    assert party_from_orm(party_to_orm(party)) == party

    group = ParliamentaryGroup(
        id="ECO-SOL", name="Groupe Écologiste", short_name="Écologistes", chamber="assemblee"
    )
    assert parliamentary_group_from_orm(parliamentary_group_to_orm(group)) == group


def test_source_document_and_chunk_roundtrip() -> None:
    doc = SourceDocument(
        kind=SourceKind.PROGRAMME,
        url="https://example.org/prog.pdf",
        sha256="b" * 64,
        storage_path="var/pdf/prog.pdf",
    )
    assert source_document_from_orm(source_document_to_orm(doc)) == doc

    chunk = DocumentChunk(
        document_id=doc.id,
        page_start=1,
        page_end=3,
        text="Texte analysé",
        embedding=[0.2] * 1024,
    )
    assert document_chunk_from_orm(document_chunk_to_orm(chunk)) == chunk


def test_proposal_and_claims_roundtrip() -> None:
    proposal = Proposal(
        candidate_id=uuid7(),
        source_document_id=uuid7(),
        page=5,
        exact_text="Texte de proposition",
        theme=Theme.ENERGIE,
    )
    assert proposal_from_orm(proposal_to_orm(proposal)) == proposal

    claim_causal = Claim(
        proposal_id=proposal.id,
        type=ClaimType.CAUSAL,
        normalized_text="Texte normalisé causal",
        causal_triple=CausalTriple(
            intervention="Intervention", mechanism="Mécanisme", outcome="Résultat"
        ),
    )
    assert claim_from_orm(claim_to_orm(claim_causal)) == claim_causal

    claim_factual = Claim(
        proposal_id=proposal.id,
        type=ClaimType.FACTUAL,
        normalized_text="Texte factuel",
        factual_statement=FactualStatement(
            statement="Constat",
            claimed_value="10 %",
            reference_value="8 %",
            source_reference="Insee",
        ),
    )
    assert claim_from_orm(claim_to_orm(claim_factual)) == claim_factual


def test_scholarly_work_and_evidence_roundtrip() -> None:
    work = ScholarlyWork(
        doi="10.1038/s41558-023-01821-2",
        openalex_id="W12345",
        title="Titre publication",
        year=2024,
        venue="Revue scientifique",
        sms_level=4,
        is_systematic_review=True,
        authors=["Dupont", "Durand"],
    )
    assert scholarly_work_from_orm(scholarly_work_to_orm(work)) == work

    query = EvidenceQuery(
        claim_id=uuid7(),
        source="openalex",
        exact_query="q=test",
        parameters={"page": 1},
        results_count=5,
    )
    assert evidence_query_from_orm(evidence_query_to_orm(query)) == query

    item = EvidenceItem(
        claim_id=query.claim_id,
        work_id=work.id,
        direction=EvidenceDirection.SUPPORTS,
        exact_quote="Citation exacte de preuve.",
        page=12,
    )
    assert evidence_item_from_orm(evidence_item_to_orm(item)) == item


def test_assessment_and_review_roundtrip() -> None:
    ass_id = uuid7()
    rev_id = uuid7()
    item_id = uuid7()

    reviewer = Reviewer(
        id=rev_id,
        public_name="Pr. Martin",
        orcid="0000-0002-1825-0097",
        disciplines=["Économie"],
        conflict_of_interest="Aucun conflit.",
    )
    assert reviewer_from_orm(reviewer_to_orm(reviewer)) == reviewer

    review = Review(
        assessment_id=ass_id,
        version=1,
        reviewer_id=rev_id,
        decision=ReviewDecision.APPROVED,
        comments="Validé sans réserve",
        duration_minutes=30,
    )
    assert review_from_orm(review_to_orm(review)) == review

    assessment = Assessment(
        id=ass_id,
        claim_id=uuid7(),
        version=1,
        status=ReviewStatus.APPROVED,
        consensus_level=ConsensusLevel.STRONG,
        evidence_direction=EvidenceDirection.SUPPORTS,
        sms_max=4,
        summary="Résumé concis.",
        sections=AssessmentSections(
            diagnostic="Diag",
            mechanism="Méc",
            evidence="Preuves",
            blind_spots="Angles morts",
            success_conditions="Conditions",
            controversies="Controverses",
        ),
        sentences=[
            Sentence(
                text="Phrase étayée.",
                kind=SentenceKind.STATEMENT,
                citations=[item_id],
            )
        ],
        reviews=[review],
        synthesiser_model="gemini-4-argon",
    )
    orm = assessment_to_orm(assessment)
    orm.reviews = [review_to_orm(review)]
    recovered = assessment_from_orm(orm)
    assert recovered == assessment


def test_verification_report_and_changelog_roundtrip() -> None:
    report = VerificationReport(
        assessment_id=uuid7(),
        version=1,
        verifier_model="gemini-3.5-flash-lite",
        same_provider=True,
        controls={"citation_support": "supported"},
        flags=["warning_numbers"],
        is_valid=True,
    )
    assert verification_report_from_orm(verification_report_to_orm(report)) == report

    entry = ChangelogEntry(
        assessment_id=report.assessment_id,
        version=1,
        reason="Mise à jour des sources",
        author="Relecteur",
    )
    assert changelog_entry_from_orm(changelog_entry_to_orm(entry)) == entry


def test_parliamentary_roundtrip() -> None:
    now = datetime.now(UTC)
    scrutin = Scrutin(
        id="VTANR5L17V0001",
        title="Scrutin solennel",
        date=now,
        solemn=True,
        result="adopté",
        dossier_id="DOS001",
    )
    assert scrutin_from_orm(scrutin_to_orm(scrutin)) == scrutin

    vote = Vote(
        scrutin_id=scrutin.id,
        deputy_name="Jean Député",
        group_id="ECO-SOL",
        position=VotePosition.POUR,
    )
    assert vote_from_orm(vote_to_orm(vote)) == vote

    amendment = Amendment(
        id="AMANR5L17001",
        dossier_id="DOS001",
        article="Article 1er",
        authors=["Auteur A"],
        expose_motifs="Motifs",
        dispositif="Dispositif",
        sort="adopté",
    )
    assert amendment_from_orm(amendment_to_orm(amendment)) == amendment


def test_llm_call_and_rectification_roundtrip() -> None:
    call = LlmCall(
        prompt_id="synthesis",
        prompt_version="1.0",
        prompt_sha="c" * 64,
        provider="gemini",
        model="gemini-4-argon",
        tier=LlmTier.FREE,
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.0,
    )
    assert llm_call_from_orm(llm_call_to_orm(call)) == call

    rect = RectificationRequest(
        assessment_id=uuid7(),
        reason="Erreur factuelle",
        proposed_doi="10.1016/j.test",
        status=RectificationStatus.RECEIVED,
    )
    assert rectification_request_from_orm(rectification_request_to_orm(rect)) == rect
