"""Fonctions de conversion bidirectionnelle entre contrats Pydantic et modèles ORM."""

from __future__ import annotations

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
from csc.db.models import (
    AmendmentModel,
    AssessmentModel,
    CandidateModel,
    ChangelogEntryModel,
    ClaimModel,
    DocumentChunkModel,
    EvidenceItemModel,
    EvidenceQueryModel,
    LlmCallModel,
    ParliamentaryGroupModel,
    PartyModel,
    ProposalModel,
    RectificationRequestModel,
    ReviewerModel,
    ReviewModel,
    ScholarlyWorkModel,
    ScrutinModel,
    SourceDocumentModel,
    VerificationReportModel,
    VoteModel,
)


def candidate_to_orm(c: Candidate) -> CandidateModel:
    return CandidateModel(
        id=c.id,
        slug=c.slug,
        name=c.name,
        parties=list(c.parties),
        parliamentary_group_id=c.parliamentary_group_id,
        status=c.status.value,
        photo_url=c.photo_url,
    )


def candidate_from_orm(m: CandidateModel) -> Candidate:
    return Candidate(
        id=m.id,
        slug=m.slug,
        name=m.name,
        parties=list(m.parties or []),
        parliamentary_group_id=m.parliamentary_group_id,
        status=CandidateStatus(m.status),
        photo_url=m.photo_url,
    )


def party_to_orm(p: Party) -> PartyModel:
    return PartyModel(
        id=p.id,
        name=p.name,
        short_name=p.short_name,
        color_hex=p.color_hex,
    )


def party_from_orm(m: PartyModel) -> Party:
    return Party(
        id=m.id,
        name=m.name,
        short_name=m.short_name,
        color_hex=m.color_hex,
    )


def parliamentary_group_to_orm(g: ParliamentaryGroup) -> ParliamentaryGroupModel:
    return ParliamentaryGroupModel(
        id=g.id,
        name=g.name,
        short_name=g.short_name,
        chamber=g.chamber,
    )


def parliamentary_group_from_orm(m: ParliamentaryGroupModel) -> ParliamentaryGroup:
    return ParliamentaryGroup(
        id=m.id,
        name=m.name,
        short_name=m.short_name,
        chamber=m.chamber,
    )


def source_document_to_orm(d: SourceDocument) -> SourceDocumentModel:
    return SourceDocumentModel(
        id=d.id,
        kind=d.kind.value,
        url=d.url,
        sha256=d.sha256,
        retrieved_at=d.retrieved_at,
        licence=d.licence,
        robots_allowed=d.robots_allowed,
        tdm_optout=d.tdm_optout,
        storage_path=d.storage_path,
    )


def source_document_from_orm(m: SourceDocumentModel) -> SourceDocument:
    return SourceDocument(
        id=m.id,
        kind=SourceKind(m.kind),
        url=m.url,
        sha256=m.sha256,
        retrieved_at=m.retrieved_at,
        licence=m.licence,
        robots_allowed=m.robots_allowed,
        tdm_optout=m.tdm_optout,
        storage_path=m.storage_path,
    )


def document_chunk_to_orm(c: DocumentChunk) -> DocumentChunkModel:
    return DocumentChunkModel(
        id=c.id,
        document_id=c.document_id,
        page_start=c.page_start,
        page_end=c.page_end,
        text=c.text,
        embedding=c.embedding,
        embedding_model=c.embedding_model,
    )


def document_chunk_from_orm(m: DocumentChunkModel) -> DocumentChunk:
    emb = list(m.embedding) if m.embedding is not None else None
    return DocumentChunk(
        id=m.id,
        document_id=m.document_id,
        page_start=m.page_start,
        page_end=m.page_end,
        text=m.text,
        embedding=emb,
        embedding_model=m.embedding_model,
    )


def proposal_to_orm(p: Proposal) -> ProposalModel:
    return ProposalModel(
        id=p.id,
        candidate_id=p.candidate_id,
        source_document_id=p.source_document_id,
        page=p.page,
        exact_text=p.exact_text,
        theme=p.theme.value,
        selected_by_rule=p.selected_by_rule,
        selection_reason=p.selection_reason,
    )


def proposal_from_orm(m: ProposalModel) -> Proposal:
    return Proposal(
        id=m.id,
        candidate_id=m.candidate_id,
        source_document_id=m.source_document_id,
        page=m.page,
        exact_text=m.exact_text,
        theme=Theme(m.theme),
        selected_by_rule=m.selected_by_rule,
        selection_reason=m.selection_reason,
    )


def claim_to_orm(c: Claim) -> ClaimModel:
    causal_dict = c.causal_triple.model_dump() if c.causal_triple else None
    factual_dict = c.factual_statement.model_dump() if c.factual_statement else None
    return ClaimModel(
        id=c.id,
        proposal_id=c.proposal_id,
        type=c.type.value,
        normalized_text=c.normalized_text,
        causal_triple=causal_dict,
        factual_statement=factual_dict,
    )


def claim_from_orm(m: ClaimModel) -> Claim:
    causal_triple = CausalTriple(**m.causal_triple) if m.causal_triple else None
    factual_stmt = FactualStatement(**m.factual_statement) if m.factual_statement else None
    return Claim(
        id=m.id,
        proposal_id=m.proposal_id,
        type=ClaimType(m.type),
        normalized_text=m.normalized_text,
        causal_triple=causal_triple,
        factual_statement=factual_stmt,
    )


def scholarly_work_to_orm(w: ScholarlyWork) -> ScholarlyWorkModel:
    return ScholarlyWorkModel(
        id=w.id,
        doi=w.doi,
        openalex_id=w.openalex_id,
        hal_id=w.hal_id,
        s2_id=w.s2_id,
        title=w.title,
        year=w.year,
        venue=w.venue,
        cited_by_count=w.cited_by_count,
        abstract=w.abstract,
        design=w.design,
        sms_level=w.sms_level,
        is_systematic_review=w.is_systematic_review,
        authors=list(w.authors),
        url=w.url,
    )


def scholarly_work_from_orm(m: ScholarlyWorkModel) -> ScholarlyWork:
    return ScholarlyWork(
        id=m.id,
        doi=m.doi,
        openalex_id=m.openalex_id,
        hal_id=m.hal_id,
        s2_id=m.s2_id,
        title=m.title,
        year=m.year,
        venue=m.venue,
        cited_by_count=m.cited_by_count,
        abstract=m.abstract,
        design=m.design,
        sms_level=m.sms_level,
        is_systematic_review=m.is_systematic_review,
        authors=list(m.authors or []),
        url=m.url,
    )


def evidence_query_to_orm(q: EvidenceQuery) -> EvidenceQueryModel:
    return EvidenceQueryModel(
        id=q.id,
        claim_id=q.claim_id,
        source=q.source,
        exact_query=q.exact_query,
        parameters=dict(q.parameters),
        queried_at=q.queried_at,
        results_count=q.results_count,
    )


def evidence_query_from_orm(m: EvidenceQueryModel) -> EvidenceQuery:
    return EvidenceQuery(
        id=m.id,
        claim_id=m.claim_id,
        source=m.source,
        exact_query=m.exact_query,
        parameters=dict(m.parameters or {}),
        queried_at=m.queried_at,
        results_count=m.results_count,
    )


def evidence_item_to_orm(e: EvidenceItem) -> EvidenceItemModel:
    return EvidenceItemModel(
        id=e.id,
        claim_id=e.claim_id,
        work_id=e.work_id,
        chunk_id=e.chunk_id,
        relevance=e.relevance,
        direction=e.direction.value,
        exact_quote=e.exact_quote,
        page=e.page,
    )


def evidence_item_from_orm(m: EvidenceItemModel) -> EvidenceItem:
    return EvidenceItem(
        id=m.id,
        claim_id=m.claim_id,
        work_id=m.work_id,
        chunk_id=m.chunk_id,
        relevance=m.relevance,
        direction=EvidenceDirection(m.direction),
        exact_quote=m.exact_quote,
        page=m.page,
    )


def assessment_to_orm(a: Assessment) -> AssessmentModel:
    return AssessmentModel(
        id=a.id,
        claim_id=a.claim_id,
        version=a.version,
        status=a.status.value,
        factual_verdict=a.factual_verdict.value if a.factual_verdict else None,
        consensus_level=a.consensus_level.value if a.consensus_level else None,
        evidence_direction=a.evidence_direction.value if a.evidence_direction else None,
        sms_max=a.sms_max,
        summary=a.summary,
        sections=a.sections.model_dump(),
        sentences=[s.model_dump(mode="json") for s in a.sentences],
        limitations=a.limitations,
        synthesiser_model=a.synthesiser_model,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def assessment_from_orm(m: AssessmentModel) -> Assessment:
    sections_dict = dict(m.sections or {})
    sections = AssessmentSections(**sections_dict)

    sentences: list[Sentence] = []
    for s_raw in m.sentences or []:
        s_dict = dict(s_raw)
        sentences.append(
            Sentence(
                id=s_dict["id"],
                text=s_dict["text"],
                kind=SentenceKind(s_dict.get("kind", SentenceKind.STATEMENT.value)),
                citations=s_dict.get("citations", []),
            )
        )

    reviews = [review_from_orm(r) for r in getattr(m, "reviews", [])]

    return Assessment(
        id=m.id,
        claim_id=m.claim_id,
        version=m.version,
        status=ReviewStatus(m.status),
        factual_verdict=FactualVerdict(m.factual_verdict) if m.factual_verdict else None,
        consensus_level=ConsensusLevel(m.consensus_level) if m.consensus_level else None,
        evidence_direction=EvidenceDirection(m.evidence_direction)
        if m.evidence_direction
        else None,
        sms_max=m.sms_max,
        summary=m.summary,
        sections=sections,
        sentences=sentences,
        reviews=reviews,
        limitations=m.limitations,
        synthesiser_model=m.synthesiser_model,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def reviewer_to_orm(r: Reviewer) -> ReviewerModel:
    return ReviewerModel(
        id=r.id,
        public_name=r.public_name,
        orcid=r.orcid,
        openalex_author_id=r.openalex_author_id,
        disciplines=list(r.disciplines),
        conflict_of_interest=r.conflict_of_interest,
    )


def reviewer_from_orm(m: ReviewerModel) -> Reviewer:
    return Reviewer(
        id=m.id,
        public_name=m.public_name,
        orcid=m.orcid,
        openalex_author_id=m.openalex_author_id,
        disciplines=list(m.disciplines or []),
        conflict_of_interest=m.conflict_of_interest,
    )


def review_to_orm(r: Review) -> ReviewModel:
    return ReviewModel(
        id=r.id,
        assessment_id=r.assessment_id,
        version=r.version,
        reviewer_id=r.reviewer_id,
        decision=r.decision.value,
        comments=r.comments,
        submitted_at=r.submitted_at,
        duration_minutes=r.duration_minutes,
    )


def review_from_orm(m: ReviewModel) -> Review:
    return Review(
        id=m.id,
        assessment_id=m.assessment_id,
        version=m.version,
        reviewer_id=m.reviewer_id,
        decision=ReviewDecision(m.decision),
        comments=m.comments,
        submitted_at=m.submitted_at,
        duration_minutes=m.duration_minutes,
    )


def verification_report_to_orm(v: VerificationReport) -> VerificationReportModel:
    return VerificationReportModel(
        id=v.id,
        assessment_id=v.assessment_id,
        version=v.version,
        verifier_model=v.verifier_model,
        same_provider=v.same_provider,
        controls=dict(v.controls),
        flags=list(v.flags),
        is_valid=v.is_valid,
        created_at=v.created_at,
    )


def verification_report_from_orm(m: VerificationReportModel) -> VerificationReport:
    return VerificationReport(
        id=m.id,
        assessment_id=m.assessment_id,
        version=m.version,
        verifier_model=m.verifier_model,
        same_provider=m.same_provider,
        controls=dict(m.controls or {}),
        flags=list(m.flags or []),
        is_valid=m.is_valid,
        created_at=m.created_at,
    )


def changelog_entry_to_orm(e: ChangelogEntry) -> ChangelogEntryModel:
    return ChangelogEntryModel(
        id=e.id,
        assessment_id=e.assessment_id,
        version=e.version,
        changed_at=e.changed_at,
        reason=e.reason,
        author=e.author,
    )


def changelog_entry_from_orm(m: ChangelogEntryModel) -> ChangelogEntry:
    return ChangelogEntry(
        id=m.id,
        assessment_id=m.assessment_id,
        version=m.version,
        changed_at=m.changed_at,
        reason=m.reason,
        author=m.author,
    )


def scrutin_to_orm(s: Scrutin) -> ScrutinModel:
    return ScrutinModel(
        id=s.id,
        chamber=s.chamber,
        title=s.title,
        date=s.date,
        solemn=s.solemn,
        result=s.result,
        dossier_id=s.dossier_id,
    )


def scrutin_from_orm(m: ScrutinModel) -> Scrutin:
    return Scrutin(
        id=m.id,
        chamber=m.chamber,
        title=m.title,
        date=m.date,
        solemn=m.solemn,
        result=m.result,
        dossier_id=m.dossier_id,
    )


def vote_to_orm(v: Vote) -> VoteModel:
    return VoteModel(
        id=v.id,
        scrutin_id=v.scrutin_id,
        deputy_name=v.deputy_name,
        group_id=v.group_id,
        position=v.position.value,
    )


def vote_from_orm(m: VoteModel) -> Vote:
    return Vote(
        id=m.id,
        scrutin_id=m.scrutin_id,
        deputy_name=m.deputy_name,
        group_id=m.group_id,
        position=VotePosition(m.position),
    )


def amendment_to_orm(a: Amendment) -> AmendmentModel:
    return AmendmentModel(
        id=a.id,
        dossier_id=a.dossier_id,
        article=a.article,
        authors=list(a.authors),
        group_id=a.group_id,
        expose_motifs=a.expose_motifs,
        dispositif=a.dispositif,
        sort=a.sort,
        scrutin_id=a.scrutin_id,
    )


def amendment_from_orm(m: AmendmentModel) -> Amendment:
    return Amendment(
        id=m.id,
        dossier_id=m.dossier_id,
        article=m.article,
        authors=list(m.authors or []),
        group_id=m.group_id,
        expose_motifs=m.expose_motifs,
        dispositif=m.dispositif,
        sort=m.sort,
        scrutin_id=m.scrutin_id,
    )


def llm_call_to_orm(call: LlmCall) -> LlmCallModel:
    return LlmCallModel(
        id=call.id,
        prompt_id=call.prompt_id,
        prompt_version=call.prompt_version,
        prompt_sha=call.prompt_sha,
        provider=call.provider,
        model=call.model,
        tier=call.tier.value,
        batch_job_id=call.batch_job_id,
        params=dict(call.params),
        input_tokens=call.input_tokens,
        cached_tokens=call.cached_tokens,
        output_tokens=call.output_tokens,
        thinking_tokens=call.thinking_tokens,
        cost_usd=call.cost_usd,
        latency_ms=call.latency_ms,
        raw_output=call.raw_output,
        created_at=call.created_at,
    )


def llm_call_from_orm(m: LlmCallModel) -> LlmCall:
    return LlmCall(
        id=m.id,
        prompt_id=m.prompt_id,
        prompt_version=m.prompt_version,
        prompt_sha=m.prompt_sha,
        provider=m.provider,
        model=m.model,
        tier=LlmTier(m.tier),
        batch_job_id=m.batch_job_id,
        params=dict(m.params or {}),
        input_tokens=m.input_tokens,
        cached_tokens=m.cached_tokens,
        output_tokens=m.output_tokens,
        thinking_tokens=m.thinking_tokens,
        cost_usd=m.cost_usd,
        latency_ms=m.latency_ms,
        raw_output=m.raw_output,
        created_at=m.created_at,
    )


def rectification_request_to_orm(r: RectificationRequest) -> RectificationRequestModel:
    return RectificationRequestModel(
        id=r.id,
        assessment_id=r.assessment_id,
        reason=r.reason,
        proposed_doi=r.proposed_doi,
        email=r.email,
        received_at=r.received_at,
        imported_at=r.imported_at,
        status=r.status.value,
        public_response=r.public_response,
    )


def rectification_request_from_orm(m: RectificationRequestModel) -> RectificationRequest:
    return RectificationRequest(
        id=m.id,
        assessment_id=m.assessment_id,
        reason=m.reason,
        proposed_doi=m.proposed_doi,
        email=m.email,
        received_at=m.received_at,
        imported_at=m.imported_at,
        status=RectificationStatus(m.status),
        public_response=m.public_response,
    )
