# L08 — Ingestion documentaire et index RAG (local, CPU)

**Agent** : standard · **Dépend de** : L02, L03 (embeddings) · **Effort** : 2 j
**Fichiers autorisés** : `backend/src/csc/ingest/`, `data/editorial/sources.yaml`, `backend/tests/ingest/`

## Objectif
Transformer les PDF et pages web (programmes, professions de foi, rapports institutionnels) en **texte ancré à la page**, découpé et vectorisé, avec un **registre de provenance** juridiquement défendable.

## Pourquoi ne pas tout mettre en *context caching*
Le rapport Gemini proposait de charger le GIEC AR6, le HCC, l'IPP… dans le cache de contexte. Ce corpus fait des dizaines de milliers de pages, bien plus qu'une fenêtre de contexte, et le stockage en cache est facturé à l'heure. On adopte donc un **RAG entièrement local** :
1. index vectoriel `pgvector` de tout le corpus, ancré à la page, construit **sur le CPU du PC** (0 $) ;
2. pour chaque fiche, L10 assemble un **dossier de preuves** compact (**≤ 25k tokens**), seul envoyé au LLM.

## Tâches
1. **Registre `data/editorial/sources.yaml`** : URL, éditeur, type, licence, priorité. Corpus initial à compléter par un humain :
   - rapports annuels du HCC 2024–2026 ;
   - **résumés pour décideurs (SPM) et résumés techniques** du GIEC AR6, plutôt que les rapports complets ;
   - IPP et OFCE (chiffrages et évaluations), France Stratégie (devenu Haut-commissariat à la stratégie et au plan), I4CE ;
   - Cour des comptes, CNESCO, INRAE, Conseil d'analyse économique.
2. **Collecteur** respectant le CPI L.122-5-3 (TDM) :
   - lire `robots.txt` et les métadonnées d'opposition (`tdm-reservation`, CGU) et stocker `robots_allowed` et `tdm_optout` ;
   - **ne pas collecter** si une opposition est exprimée (sauf source publique ou ouverte) ;
   - User-Agent identifiable avec URL de contact ;
   - stockage sécurisé, accès restreint, SHA-256 et date.
3. **Parsing local avec Docling sur CPU** : texte, tableaux et numéros de page.
   - OCR **désactivé** par défaut (PDF natifs, beaucoup plus rapide) ; OCR Tesseract local seulement pour les PDF détectés comme scannés.
   - Traitement parallèle par document (`--workers` = nombre de cœurs / 2), reprenable, avec cache du résultat Docling (JSON) dans `var/cache/docling/` indexé par SHA-256.
   - Installer les roues **CPU** (pas de CUDA).
4. **Découpage** par section avec chevauchement (~800 tokens). Chaque chunk garde `page_start` et `page_end` ; les tableaux ne sont jamais coupés.
5. **Embeddings locaux** via `csc.embed` (L03) : `fastembed` avec `intfloat/multilingual-e5-large`, préfixe `"passage: "`. Stockés en `vector(1024)` avec un index HNSW. Mesurer et consigner le débit (chunks/s) dans le README.
6. **Recherche** : `search_chunks(query, k, filters={publisher, year, kind}) -> list[DocumentChunk]`, hybride (BM25 via `tsvector` français et vecteur, fusion RRF).
7. **Programmes** : `ingest_programme(candidate_slug, url_or_pdf)` et `ingest_profession_de_foi(...)` (format FALC quand il existe).

## Critères d'acceptation
- Sur 3 PDF de test committés (dont un avec tableau), les numéros de page sont exacts dans 100 % des chunks testés.
- Un document avec `tdm_optout = true` n'est jamais téléchargé (test).
- Requête « coût d'abattement taxe carbone » sur l'échantillon : le bon chunk sort dans le top 5, **y compris quand le passage est en anglais** (recherche multilingue).
- Tout le lot tourne sans GPU et sans aucun appel d'API payante.
