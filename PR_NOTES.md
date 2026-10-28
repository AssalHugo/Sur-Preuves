# Notes de Révision — Lot L02 : Modèle de données et contrats

## 1. Contexte et Objectifs
Le lot L02 constitue la colonne vertébrale du projet **Comparateur Science 2027**. Il a pour mission de définir de manière unifiée et immuable les contrats de données échangés entre tous les pipelines (ingestion, extraction, recherche documentaire, synthèse LLM, vérification, relecture et site statique).

Tous les critères d'acceptation du document de lot `plan/lots/L02-modele-donnees-contrats.md` sont atteints à 100 %, sans contournement ni warning.

---

## 2. Modifications Réalisées

### A. Énumérations Métier (`backend/src/csc/contracts/enums.py`)
- `ClaimType` : `normative`, `factual`, `causal`.
- `FactualVerdict` : `accurate`, `approximate`, `misleading`, `inaccurate`, `unverifiable`.
- `EvidenceDirection` : `supports`, `mixed`, `contradicts`, `inconclusive`.
- `ConsensusLevel` : `strong`, `emerging`, `contested`, `insufficient_evidence`, `novel_no_ex_post`.
- `SmsLevel` : Maryland Scientific Methods Scale (1 à 5).
- `Theme` : Taxonomie complète de 15 thèmes de politiques publiques.
- `ReviewStatus` : Workflow éditorial complet (`ai_draft` → `in_review` → `changes_requested` → `approved` → `published` | `withdrawn`).
- `SourceKind` : Documents sources (`programme`, `profession_de_foi`, `amendment`, `vote`, `scholarly_work`, `institutional_report`).
- Énumérations complémentaires pour les lots aval : `CandidateStatus`, `SentenceKind`, `ReviewDecision`, `CitationSupportVerdict`, `LlmTier`, `RectificationStatus`, `VotePosition`.

### B. Identifiants Stables UUIDv7 (`backend/src/csc/contracts/uuid_v7.py`)
- Implémentation conforme **RFC 9562** sans dépendance externe C :
  - Tri chronologique garanti (compteur monotone au sein de la milliseconde).
  - Version 7 et variante RFC 4122 standardisées.
  - Adapté aux identifiants stables dans les URL publiques.

### C. Modèles Pydantic v2 & Validations (`backend/src/csc/contracts/models.py`)
- Implémentation des 20 entités métier : `Candidate`, `Party`, `ParliamentaryGroup`, `SourceDocument`, `DocumentChunk` (dim 1024), `Proposal`, `CausalTriple`, `FactualStatement`, `Claim`, `ScholarlyWork`, `EvidenceQuery`, `EvidenceItem`, `Sentence`, `AssessmentSections`, `Reviewer`, `Review`, `Assessment`, `VerificationReport`, `ChangelogEntry`, `Scrutin`, `Vote`, `Amendment`, `LlmCall`, `RectificationRequest`.
- Validations métier obligatoires :
  1. `Sentence` : obligation d'au moins une citation d'`EvidenceItem` pour toute phrase non contextuelle (`kind != SentenceKind.CONTEXT`).
  2. `Assessment` : interdiction du statut `approved` ou `published` sans au moins une relecture validée (`ReviewDecision.APPROVED`).

### D. Modèles ORM & Persistance (`backend/src/csc/db/`)
- Modèles SQLAlchemy 2.0 (`backend/src/csc/db/models.py`) avec types stricts, clés primaires UUID, clés étrangères avec cascade appropriée et colonne `Vector(1024)` pgvector sur `document_chunks`.
- Fonctions de conversion bidirectionnelle exhaustives (`backend/src/csc/db/conversion.py`) testées en aller-retour sans perte.
- Sessions transactionnelles et vérification d'extension (`backend/src/csc/db/session.py`).

### E. Migrations Alembic (`backend/alembic/`)
- Migration initiale `0001_initial_schema.py` :
  - Active `CREATE EXTENSION IF NOT EXISTS vector;` sur PostgreSQL.
  - Crée les 20 tables et index associés.
  - Procédure de downgrade réversible intégrale.
- Intégration CLI : `csc db migrate` et `make db-migrate` exécutent automatiquement les migrations Alembic.

### F. Schémas Éditoriaux YAML (`data/editorial/`)
- `candidates.schema.yaml` et `candidates.sample.yaml` : validation des profils candidats.
- `parties.schema.yaml` et `parties.sample.yaml` : validation des partis politiques et codes couleurs.
- `groupes_partis.schema.yaml`, `groupes_partis.sample.yaml` et `groupes_partis.yaml` : table de correspondance humaine groupe parlementaire ↔ parti ↔ candidat.

### G. Bundle de Publication & Fixtures (`web/src/fixtures/` et `web/src/schema/`)
- `web/src/schema/bundle.schema.json` : JSON Schema draft 2020-12 généré depuis `PublicationBundle`.
- `web/src/fixtures/bundle.sample.json` : jeu de données de référence :
  - 3 candidats fictifs réalistes (`claire-delacroix`, `alexandre-leroy`, `mariam-diallo`).
  - 15 thèmes de politiques publiques documentés en français.
  - 10 fiches d'évaluation approuvées avec relectures humaines, traçabilité de requêtes et historique.
  - **Couverture exhaustive des 10 verdicts** : 5 factuels (`accurate`, `approximate`, `misleading`, `inaccurate`, `unverifiable`) + 5 consensus causaux (`strong`, `emerging`, `contested`, `insufficient_evidence`, `novel_no_ex_post`).
  - Mentions d'information IA conformes à l'Art. 50 de l'AI Act.

---

## 3. Résultats des Tests et Contrôles Qualité

La commande `make check` est verte à 100 % :
1. **Formatage Python (`ruff format`)** : 100 % conforme.
2. **Linting Python (`ruff check`)** : 0 erreur, 0 avertissement.
3. **Typage strict (`mypy --strict`)** : 0 erreur sur 26 fichiers source.
4. **Tests Python (`pytest`)** :
   - **66 tests passés avec succès** (unitaires, intégration DB, migrations Alembic, validation schémas YAML/JSON).
   - **Couverture de code sur `csc.contracts` : 100 %** (objectif minimal : ≥ 90 %).
   - Aller-retour Pydantic ↔ ORM testé pour l'ensemble des 20 entités.
   - Cycle `downgrade base` puis `upgrade head` testé avec succès sur PostgreSQL + pgvector.
5. **Site statique Astro** :
   - `astro check` : 0 erreur, 0 avertissement.
   - `astro build` : 100 % vert.

---

## 4. Limites et Prochaines Étapes
- Le lot L02 n'inclut aucune logique de calcul ou d'appel LLM (conformément à l'interdiction de logique métier dans les contrats).
- Les lots L03 (couche LLM et embeddings CPU) et L04 à L07 (connecteurs OpenAlex, HAL, Semantic Scholar, NosParlementaires) peuvent désormais s'appuyer directement sur ces contrats sans risque de rupture d'interface.
