"""Tests unitaires pour les modèles Pydantic métier (csc.contracts.models)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

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
    Candidate,
    CausalTriple,
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


def test_candidate_creation_and_defaults() -> None:
    c = Candidate(slug="jean-dupont", name="Jean Dupont", parties=["PES"])
    assert isinstance(c.id, UUID)
    assert c.status == CandidateStatus.DECLARED
    assert c.slug == "jean-dupont"
    assert c.parliamentary_group_id is None


def test_party_and_parliamentary_group() -> None:
    party = Party(id="PES", name="Parti Écologique", short_name="Écolo", color_hex="#10b981")
    assert party.id == "PES"
    assert party.color_hex == "#10b981"

    group = ParliamentaryGroup(
        id="ECO-SOL", name="Groupe Écologiste", short_name="Écologistes", chamber="assemblee"
    )
    assert group.chamber == "assemblee"


def test_source_document_and_chunk() -> None:
    doc = SourceDocument(
        kind=SourceKind.PROGRAMME,
        url="https://example.org/prog.pdf",
        sha256="a" * 64,
        storage_path="var/pdf/prog.pdf",
    )
    assert doc.licence == "Licence Ouverte 2.0"
    assert doc.robots_allowed is True
    assert doc.tdm_optout is False

    chunk = DocumentChunk(
        document_id=doc.id,
        page_start=1,
        page_end=2,
        text="Extrait de texte",
        embedding=[0.1] * 1024,
    )
    assert chunk.page_start == 1
    assert chunk.embedding_model == "intfloat/multilingual-e5-large"


def test_proposal_and_claim() -> None:
    doc_id = uuid7()
    c_id = uuid7()

    proposal = Proposal(
        candidate_id=c_id,
        source_document_id=doc_id,
        page=4,
        exact_text="Nous réduirons la TVA à 5,5 % sur les transports.",
        theme=Theme.TRANSPORT,
    )
    assert proposal.selected_by_rule is True

    claim_causal = Claim(
        proposal_id=proposal.id,
        type=ClaimType.CAUSAL,
        normalized_text="La baisse de TVA sur les transports accroît l'usage du train.",
        causal_triple=CausalTriple(
            intervention="Baisse de TVA de 10 % à 5,5 %",
            mechanism="Réduction du prix des billets ferroviaires",
            outcome="Hausse de la fréquentation ferroviaire",
        ),
    )
    assert claim_causal.type == ClaimType.CAUSAL
    assert claim_causal.causal_triple is not None
    assert claim_causal.factual_statement is None

    claim_factual = Claim(
        proposal_id=proposal.id,
        type=ClaimType.FACTUAL,
        normalized_text="Le déficit a atteint 5,5 % en 2023.",
        factual_statement=FactualStatement(
            statement="Déficit 2023 à 5,5 % du PIB",
            claimed_value="5,5 %",
            reference_value="5,54 %",
            source_reference="Insee",
        ),
    )
    assert claim_factual.type == ClaimType.FACTUAL
    assert claim_factual.factual_statement is not None


def test_scholarly_work_and_evidence() -> None:
    work = ScholarlyWork(
        doi="10.1038/s41558-023-01821-2",
        title="Decarbonization in France",
        year=2024,
        venue="Nature Climate Change",
        sms_level=4,
        is_systematic_review=True,
        authors=["Dupont, J."],
    )
    assert work.is_systematic_review is True
    assert work.sms_level == 4

    query = EvidenceQuery(
        claim_id=uuid7(),
        source="openalex",
        exact_query='title.search:"carbon emissions"',
        results_count=10,
    )
    assert query.results_count == 10

    item = EvidenceItem(
        claim_id=query.claim_id,
        work_id=work.id,
        direction=EvidenceDirection.SUPPORTS,
        exact_quote="Les émissions ont baissé de façon significative.",
        page=15,
    )
    assert item.direction == EvidenceDirection.SUPPORTS


def test_sentence_citation_validation() -> None:
    item_id = uuid7()

    # Phrase avec citation : valide
    s_valid = Sentence(
        text="La mesure entraîne une baisse observée de 5 %.",
        kind=SentenceKind.STATEMENT,
        citations=[item_id],
    )
    assert len(s_valid.citations) == 1

    # Phrase contextuelle sans citation : valide
    s_context = Sentence(
        text="Cette synthèse repose sur les données publiques.",
        kind=SentenceKind.CONTEXT,
        citations=[],
    )
    assert s_context.kind == SentenceKind.CONTEXT

    # Phrase non contextuelle sans citation : DOIT échouer
    with pytest.raises(ValidationError) as exc_info:
        Sentence(
            text="Une affirmation sans aucune source citée.",
            kind=SentenceKind.STATEMENT,
            citations=[],
        )
    assert "au moins une citation" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info2:
        Sentence(
            text="Preuve non sourcée.",
            kind=SentenceKind.EVIDENCE,
            citations=[],
        )
    assert "au moins une citation" in str(exc_info2.value)


def test_assessment_approved_review_validation() -> None:
    claim_id = uuid7()
    reviewer_id = uuid7()
    item_id = uuid7()

    valid_sentence = Sentence(
        text="Effet positif documenté par les études.",
        kind=SentenceKind.STATEMENT,
        citations=[item_id],
    )

    approved_review = Review(
        assessment_id=uuid7(),
        reviewer_id=reviewer_id,
        decision=ReviewDecision.APPROVED,
        comments="Relecture validée sans réserve.",
    )

    changes_requested_review = Review(
        assessment_id=uuid7(),
        reviewer_id=reviewer_id,
        decision=ReviewDecision.CHANGES_REQUESTED,
        comments="Préciser les conditions de réussite.",
    )

    # 1. Brouillon sans relecture : valide
    draft = Assessment(
        claim_id=claim_id,
        status=ReviewStatus.AI_DRAFT,
        summary="Brouillon en attente de vérification.",
        sentences=[valid_sentence],
    )
    assert draft.status == ReviewStatus.AI_DRAFT

    # 2. En cours de relecture : valide sans relecture approuvée
    in_rev = Assessment(
        claim_id=claim_id,
        status=ReviewStatus.IN_REVIEW,
        summary="En cours d'examen.",
        sentences=[valid_sentence],
        reviews=[changes_requested_review],
    )
    assert in_rev.status == ReviewStatus.IN_REVIEW

    # 3. Statut APPROVED sans relecture approuvée : DOIT échouer
    with pytest.raises(ValidationError) as exc_unapproved:
        Assessment(
            claim_id=claim_id,
            status=ReviewStatus.APPROVED,
            summary="Fiche approuvée prématurément.",
            sentences=[valid_sentence],
            reviews=[],
        )
    assert "doit avoir au moins une relecture approuvée" in str(exc_unapproved.value)

    with pytest.raises(ValidationError) as exc_rejected:
        Assessment(
            claim_id=claim_id,
            status=ReviewStatus.APPROVED,
            summary="Fiche avec seulement une demande de modification.",
            sentences=[valid_sentence],
            reviews=[changes_requested_review],
        )
    assert "doit avoir au moins une relecture approuvée" in str(exc_rejected.value)

    # 4. Statut APPROVED avec relecture approuvée : valide
    appr = Assessment(
        claim_id=claim_id,
        status=ReviewStatus.APPROVED,
        consensus_level=ConsensusLevel.STRONG,
        summary="Fiche validée.",
        sentences=[valid_sentence],
        reviews=[approved_review],
    )
    assert appr.status == ReviewStatus.APPROVED

    # 5. Statut PUBLISHED avec relecture approuvée : valide
    pub = Assessment(
        claim_id=claim_id,
        status=ReviewStatus.PUBLISHED,
        consensus_level=ConsensusLevel.STRONG,
        summary="Fiche publiée.",
        sentences=[valid_sentence],
        reviews=[approved_review],
    )
    assert pub.status == ReviewStatus.PUBLISHED


def test_verification_report_and_reviewer() -> None:
    rev = Reviewer(
        public_name="Pr. Alice Dubois",
        orcid="0000-0002-1825-0097",
        disciplines=["Économie"],
        conflict_of_interest="Aucun conflit d'intérêts déclaré.",
    )
    assert rev.public_name == "Pr. Alice Dubois"

    report = VerificationReport(
        assessment_id=uuid7(),
        version=1,
        verifier_model="gemini-3.5-flash-lite",
        same_provider=True,
        controls={"doi_resolves": True, "numbers_match": True},
        flags=[],
        is_valid=True,
    )
    assert report.is_valid is True
    assert report.same_provider is True


def test_parliamentary_models() -> None:
    now = datetime.now(UTC)
    scrutin = Scrutin(
        id="VTANR5L17V0001",
        title="Vote solennel sur le projet de loi finances 2027",
        date=now,
        solemn=True,
        result="adopté",
        dossier_id="DOSLEG17001",
    )
    assert scrutin.solemn is True

    vote = Vote(
        scrutin_id=scrutin.id,
        deputy_name="Jean Dupont",
        group_id="ECO-SOL",
        position=VotePosition.POUR,
    )
    assert vote.position == VotePosition.POUR

    amendment = Amendment(
        id="AMANR5L17001",
        dossier_id="DOSLEG17001",
        article="Article 3",
        authors=["Dupont", "Martin"],
        expose_motifs="Renforcer les crédits alloués à la recherche.",
        dispositif="Le montant est augmenté de 100 millions d'euros.",
        sort="adopté",
    )
    assert amendment.article == "Article 3"


def test_llm_call_and_rectification_request() -> None:
    call = LlmCall(
        prompt_id="synthesis_causal",
        prompt_version="1.0.0",
        prompt_sha="e" * 64,
        provider="gemini",
        model="gemini-4-argon",
        tier=LlmTier.PAID,
        input_tokens=1500,
        output_tokens=400,
        cost_usd=0.045,
    )
    assert call.cost_usd == 0.045
    assert call.tier == LlmTier.PAID

    rect = RectificationRequest(
        assessment_id=uuid7(),
        reason="Une étude récente contredit l'affirmation.",
        proposed_doi="10.1038/nature12345",
        status=RectificationStatus.RECEIVED,
    )
    assert rect.status == RectificationStatus.RECEIVED
