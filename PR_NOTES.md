# Notes de Révision — Lot L05 : Connecteur HAL (Archive Ouverte Nationale)

## 1. Contexte et Objectifs
Le lot L05 met en place le connecteur vers l'archive ouverte nationale **HAL** (CCSD / CNRS, `https://api.archives-ouvertes.fr/search/?wt=json`) pour le projet **Comparateur Science 2027** (`csc`), conformément aux spécifications du document `plan/lots/L05-connecteur-hal.md` et aux règles de `AGENTS.md` :
- **Point d'accès Solr officiel** : utilisation exclusive de l'API de recherche REST Solr de HAL (`https://api.archives-ouvertes.fr/search/?wt=json`), libre d'accès et sans authentification.
- **Exclusion du serveur MCP en production** : le serveur MCP `https://api.archives-ouvertes.fr/mcp` est expérimental et prévient de réponses partielles ou hallucinées ; il est exclu du pipeline automatique et documenté dans le README comme outil d'exploration manuelle.
- **Requêtes de proximité Solr sécurisées** : construction et échappement rigoureux des clauses de proximité `'"mot1 mot2"~N'`, gérant les guillemets imbriqués, barres obliques inverses et distances négatives.
- **Filtres documentaires et temporels** : filtrage par types de documents `docType_s:(ART OR REPORT OR THESE OR COUV)` et par année de production `producedDateY_i:[2005 TO *]`.
- **Référentiel des structures de recherche utiles** : recensement et résolution des identifiants AuréHAL (`structId_i`) pour les institutions clés (INRAE, IPP, OFCE, CNRS-SHS, Sciences Po LIEPP, Paris School of Economics, CEPII, CNRS).
- **Extraction et normalisation canonique** :
  - Extraction stricte des champs demandés via `fl=` : `halId_s, doiId_s, title_s, abstract_s, authFullName_s, structName_s, producedDateY_i, docType_s, journalTitle_s, uri_s, fileMain_s`.
  - Normalisation des DOI en minuscules (sans préfixes d'URL) pour la déduplication et fusion future avec OpenAlex (L10).
  - Normalisation des identifiants HAL (retrait des préfixes d'URL et suffixes de version `v1`, `v2`...).
  - Détection automatique des revues systématiques et méta-analyses (`is_systematic_review`).
- **Traçabilité publique (`EvidenceQuery`)** : chaque requête génère un enregistrement horodaté vérifiable avec persistance optionnelle dans la table SQL `evidence_queries`.
- **Cache HTTP persistant (TTL 30 jours)** : hachage SHA-256 déterministe d'URL normalisée dans `var/cache/hal/`.
- **Résilience réseau** : retries automatiques sur HTTP 429 et 5xx avec backoff exponentiel.
- **Zéro appel réseau en test** : tests fondés sur des cassettes JSON réelles enregistrées et interception `respx`.
- **Contrats immuables** : respect absolu de la règle d'invariabilité de `backend/src/csc/contracts/`.

---

## 2. Architecture & Modules Développés

Les fichiers ont été créés dans le respect strict du découpage autorisé (`backend/src/csc/connectors/hal/` et `backend/tests/connectors/hal/`) :

### A. Modèles et Utilitaires (`csc.connectors.hal.models`)
- Modèle `ResearchStructure` : `id`, `acronym`, `name`, `description`, `aliases`.
- Dictionnaire `KNOWN_STRUCTURES` et fonction `resolve_struct_id(struct_input)` permettant d'utiliser indistinctement l'acronyme (`"IPP"`, `"OFCE"`, `"INRAE"`), les alias secondaires (`"INSHS"`, `"INRA"`) ou l'identifiant numérique (`266522`, `250936`, `577435`).
- Fonctions de normalisation et d'échappement :
  - `build_proximity_query(term1, term2, distance)` : produit `'"mot1 mot2"~N'` avec échappement des caractères spéciaux (`\`, `"`).
  - `escape_solr_phrase_term(term)` : sécurise l'inclusion de termes dans les expressions Solr.
  - `normalize_doi(doi)` : supprime les préfixes d'URL (`https://doi.org/`, `doi:`) et force les minuscules.
  - `normalize_hal_id(hal_id)` : extrait l'identifiant court sans préfixe URL ni suffixe de version (`v1`, `v2`), gère les URLs avec sous-chemins (`/document`, `/file/...`) et garantit la mise en minuscules pour la sensibilité à la casse Solr.
  - `parse_hal_doc(doc)` : transforme un document Solr brut en instance conforme du contrat immuable `ScholarlyWork`, avec détection bilingue (français et anglais) des revues systématiques et méta-analyses dans le titre et l'abstract.

### B. Cache HTTP Persistant sur Disque (`csc.connectors.hal.cache`)
- `HalHttpCache` :
  - Clé de cache = SHA-256 de l'URL normalisée avec tri déterministe des paramètres (y compris répétitions multiples de `fq`).
  - Résolution de chemin relative à la racine du dépôt `_PROJECT_ROOT / var/cache/hal/`.
  - Durée de vie par défaut de 30 jours (2 592 000 s).
  - Écriture atomique sur disque (`.tmp` puis `replace`).
  - Méthode `clear()` pour purger le cache (fichiers `.json` et fichiers temporaires orphelins `.tmp`).

### C. Client HAL Solr & Fonctions Exposées (`csc.connectors.hal.client`, `csc.connectors.hal`)
Fonctions exposées conformément à la spécification :
```python
search(query: str, *, doc_types=("ART","REPORT","THESE","COUV"), since_year=2005, rows=100,
       proximity: tuple[str, str, int] | None = None) -> list[ScholarlyWork]
search_by_structure(struct_ids: list[int], query: str) -> list[ScholarlyWork]
get(hal_id: str) -> ScholarlyWork
```
- Support d'un client singleton par défaut via `get_default_client()`.
- Gestion des sessions Keep-Alive via `httpx.Client`, avec support context manager et méthode `close()`.
- Bornage mémoire de la traçabilité des requêtes (`recorded_queries`, max 1000) et méthode `clear_recorded_queries()`.
- Traçabilité enrichie avec le volume total de documents Solr identifiés (`num_found`) dans les paramètres `EvidenceQuery`.
- Gestion résiliente des retries 429 et 5xx avec parsing tolérant du header HTTP `Retry-After` (secondes ou dates RFC).

### D. Commandes CLI Typer (`backend/src/csc/cli.py`)
- `csc hal search "<query>" [--proximity "mot1,mot2,distance"] [--doc-types ...] [--since-year ...] [--limit N]` : recherche avec tableau Rich des résultats.
- `csc hal structure <acronyme_ou_id> [--query ...] [--limit N]` : recherche filtrée sur une structure de recherche affiliée.
- `csc hal get <hal_id>` : fiche complète de métadonnées de la publication.
- `csc hal structures` : catalogue tabulé des structures françaises référencées avec leurs identifiants AuréHAL.

### E. Documentation (`README.md` et `backend/src/csc/connectors/hal/README.md`)
- Documentation de l'API Solr, de la mise en cache et de la mise à l'écart du serveur MCP.
- Tableau récapitulatif complet des identifiants AuréHAL (`structId_i`) pour les organismes de référence :
  - **IPP** : `266522`
  - **OFCE** : `250936`
  - **INRAE** : `577435`
  - **CNRS-SHS (INSHS)** : `84039`
  - **LIEPP (Sciences Po)** : `218465`
  - **PSE (Paris School of Economics)** : `301309`
  - **CEPII** : `110493`
  - **CNRS** : `441569`
- Instructions pour les relecteurs humains afin d'étendre la liste via `aurehal.hal.science`.

---

## 3. Résultats des Tests et Contrôles Qualité

La cible **`make check` est 100 % verte**, sans avertissement ni contournement :
1. **Formatage Python (`ruff format`)** : 107 fichiers vérifiés et conformes.
2. **Linting Python (`ruff check`)** : 0 erreur, 0 avertissement.
3. **Typage statique strict (`mypy --strict`)** : **0 erreur sur 78 fichiers source**.
4. **Tests Python (`pytest`)** :
   - **183 tests passés avec succès** (2 ignorés réservés aux tests live API Gemini).
   - **37 tests dédiés** au connecteur HAL :
     - Échappement et construction de requêtes de proximité (`test_models.py`).
     - Normalisation des identifiants HAL (casse, URLs avec document/file/paramètres) et des DOI (`test_models.py`).
     - Résolution des structures AuréHAL et alias (`test_models.py`).
     - Parsing complet des métadonnées, abstracts multilingues, détection des revues systématiques en français (`test_models.py`).
     - Normalisation d'URL, cache hit/miss, expiration TTL et purge (`test_cache.py`).
     - Recherche de proximité et filtres temporels sur cassette (`test_client.py`).
     - Recherche par structure affiliée (`test_client.py`).
     - Retries sur 429 (secondes et dates RFC) et 500 (`test_client.py`).
     - Traçabilité `EvidenceQuery` avec conservation de `num_found` et persistance SQL (`test_client.py`).
     - Commandes CLI `csc hal search`, `structure`, `get`, `structures` (`test_cli.py`).
5. **Compilation Web Astro (`npm run check` & `npm run build`)** : 0 erreur, génération statique réussie.
