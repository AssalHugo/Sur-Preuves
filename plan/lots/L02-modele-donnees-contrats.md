# L02 — Modèle de données et contrats

**Agent** : fort · **Dépend de** : L01 · **Effort** : 1,5 j
**Fichiers autorisés** : `backend/src/csc/contracts/`, `backend/src/csc/db/`, `backend/alembic/`, `data/editorial/` (schémas), `web/src/fixtures/`, `backend/tests/`

## Objectif
Définir **une seule fois** les objets métier que tous les lots s'échangent : modèles Pydantic, tables SQL et JSON Schema exporté pour le site. C'est le lot le plus important pour paralléliser la suite.

## Énumérations (`contracts/enums.py`)
- `ClaimType` : `normative` | `factual` | `causal`
- `FactualVerdict` : `accurate` | `approximate` | `misleading` | `inaccurate` | `unverifiable`
- `EvidenceDirection` : `supports` | `mixed` | `contradicts` | `inconclusive`
- `ConsensusLevel` : `strong` | `emerging` | `contested` | `insufficient_evidence` | `novel_no_ex_post`
- `SmsLevel` : 1..5, plus le drapeau `is_systematic_review: bool`
- `Theme` : taxonomie d'environ 15 thèmes (économie-emploi, fiscalité, retraites, santé, éducation, énergie, climat, agriculture, logement, sécurité-justice, immigration, transport, numérique, institutions, Europe-international)
- `ReviewStatus` : `ai_draft` → `in_review` → `changes_requested` → `approved` → `published` | `withdrawn`
- `SourceKind` : `programme` | `profession_de_foi` | `amendment` | `vote` | `scholarly_work` | `institutional_report`

## Entités (Pydantic, plus tables SQLAlchemy équivalentes)
| Entité | Champs clés |
|---|---|
| `Candidate` | id, slug, nom, parti(s), groupe parlementaire lié (nullable), statut (`declared` / `official`) |
| `Party`, `ParliamentaryGroup` | id, nom, sigle, correspondances (table éditoriale YAML) |
| `SourceDocument` | id, kind, url, sha256, retrieved_at, licence, robots_allowed, tdm_optout, storage_path |
| `DocumentChunk` | id, document_id, page_start, page_end, text, embedding `vector(n)` (n lu dans `config/models.yaml` ; 1024 pour `multilingual-e5-large`), embedding_model |
| `Proposal` | id, candidate_id, source_document_id, page, texte exact, thème, `selected_by_rule` (bool + motif) |
| `Claim` | id, proposal_id, type, texte normalisé, `causal_triple` {intervention, mechanism, outcome} ou `factual_statement` |
| `ScholarlyWork` | id interne, doi, openalex_id, hal_id, s2_id, titre, année, revue, cited_by_count, abstract, design, sms_level, is_systematic_review |
| `EvidenceQuery` | id, claim_id, source (openalex / hal / …), requête exacte, paramètres, date, nombre de résultats (**traçabilité publique**) |
| `EvidenceItem` | id, claim_id, work_id ou chunk_id, pertinence, direction, extrait exact |
| `Assessment` (fiche) | id, claim_id, version, verdict factuel ou niveau de consensus, sms_max, résumé, sections (diagnostic, mécanisme, preuves, angles morts, conditions de réussite, controverses), `sentences[]` |
| `Sentence` | texte, `citations[]` (ids d'`EvidenceItem` uniquement) |
| `VerificationReport` | assessment_id, version, contrôles (citation_support, doi_resolves, numbers_match, neutrality_lint, parity), drapeaux |
| `Review` | assessment_id, version, reviewer_id, décision, commentaires, horodatage, temps passé |
| `Reviewer` | id, nom public, ORCID, OpenAlex author id, disciplines, déclaration d'intérêts (données personnelles minimales) |
| `ChangelogEntry` | assessment_id, version, date, motif, auteur |
| `Scrutin`, `Vote`, `Amendment` | voir L07 |
| `LlmCall` | id, prompt_id, prompt_version, prompt_sha, provider, model, tier (`paid` / `free`), batch_job_id, params, input_tokens, cached_tokens, output_tokens, thinking_tokens, cost_usd (estimé puis réel), latency, raw_output, created_at |
| `RectificationRequest` | id, assessment_id, motif, DOI proposé, e-mail facultatif, reçu_le, importé_le, statut, réponse publique |

## Bundle de publication (`contracts/publish.py`)
Format JSON **versionné**, consommé par le site (L15) : `PublicationBundle { generated_at, schema_version, candidates[], themes[], assessments[] (approuvées seulement), works[], queries[], changelog[], ai_disclosure }`. Exporter le JSON Schema dans `web/src/schema/bundle.schema.json`. Fournir **des fixtures réalistes** dans `web/src/fixtures/bundle.sample.json` : 3 candidats fictifs, 10 fiches couvrant tous les verdicts.

## Tâches
1. Écrire les modèles Pydantic et les tables SQLAlchemy, puis la première migration Alembic (`CREATE EXTENSION vector`).
2. Ajouter les validations : une `Sentence` doit avoir au moins une citation sauf si `kind == "context"` ; un `Assessment` `approved` doit avoir au moins une `Review` approuvée.
3. Exporter le JSON Schema et générer les fixtures.
4. Écrire `data/editorial/*.schema.yaml` (candidats, partis, correspondance groupes ↔ partis) et un exemple.

## Critères d'acceptation
- `alembic upgrade head` passe sur une base vide ; aller-retour Pydantic ↔ ORM testé.
- Le JSON Schema est généré et les fixtures se valident contre lui (test).
- Couverture de tests de `contracts/` ≥ 90 %.

## Pièges
- Ne pas mettre de logique métier ici.
- Les identifiants doivent être stables (UUIDv7) : ils apparaissent dans les URL publiques.
