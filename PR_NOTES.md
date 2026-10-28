# Notes de Révision — Lot L04 : Connecteur OpenAlex

## 1. Contexte et Objectifs
Le lot L04 met en place le connecteur vers l'API scientifique **OpenAlex** (`https://api.openalex.org`) pour le projet **Comparateur Science 2027** (`csc`), conformément aux spécifications du document `plan/lots/L04-connecteur-openalex.md` et aux règles de `AGENTS.md` :
- **Budget gratuit maîtrisé** : suivi rigoureux du plafond gratuit de **1,00 $/jour** (100 000 crédits/jour) avec **arrêt propre préventif à 90 %** (`OpenAlexBudgetExceededError`).
- **Comptabilisation exacte des crédits** : lecture et persistance des en-têtes officiels `X-RateLimit-Credits-Used`, `X-RateLimit-Remaining` et `X-RateLimit-Limit`.
- **Limiteur de débit par seau à jetons (Token Bucket)** :
  - Débit requêtes générales : 10 req/s sans clé, 30 req/s avec clé API gratuite.
  - Débit recherche sémantique : 1 req/s maximum.
- **Cache HTTP persistant (TTL de 30 jours)** : hachage déterministe SHA-256 d'URL normalisée avec tri des paramètres et exclusion stricte des clés API secrètes.
- **Résilience réseau** : retries automatiques sur HTTP 429 et 5xx avec backoff exponentiel et respect du header `Retry-After`.
- **Reconstruction de texte et normalisation** :
  - Reconstitution fidèle de l'abstract depuis `abstract_inverted_index`.
  - Normalisation des DOI (minuscules, retrait des préfixes `https://doi.org/`).
  - Normalisation des identifiants OpenAlex (`W...`, `I...`, `A...`).
  - Détection automatique des revues systématiques et méta-analyses (`is_systematic_review`).
- **Traçabilité publique (`EvidenceQuery`)** : chaque interrogation génère une trace vérifiable (URL normalisée, paramètres, nombre de résultats, crédits consommés, statut cache), avec persistance optionnelle dans la table SQL `evidence_queries`.
- **Zéro appel réseau en CI** : simulation intégrale via cassettes JSON enregistrées et interception `respx`.
- **Contrats immuables** : respect absolu de la règle d'invariabilité de `backend/src/csc/contracts/`.

---

## 2. Architecture & Modules Développés

Les fichiers ont été créés dans le respect strict du découpage autorisé (`backend/src/csc/connectors/openalex/` et `backend/tests/connectors/openalex/`) :

### A. Modèles et Transformateurs (`csc.connectors.openalex.models`)
- Modèle `Institution` : `id`, `display_name`, `country_code`, `type`, `ror`, `works_count`, `cited_by_count`, `homepage_url`.
- Modèle `Author` : `id`, `display_name`, `orcid`, `works_count`, `cited_by_count`, `last_known_institution`, `last_known_institution_id` (vivier pour la relecture scientifique par les pairs - L00).
- Fonctions de normalisation et d'extraction :
  - `reconstruct_abstract(inverted_index)` : trie les index de positions ordinales et reconstruit le texte intégral du résumé.
  - `normalize_doi(doi)` : nettoie les URL et préfixes pour obtenir un DOI canonique.
  - `normalize_openalex_id(id_str)` : extrait l'identifiant court canonique (`W...`, `I...`, `A...`).
  - `work_dict_to_scholarly_work(data)` : produit une instance conforme du contrat immuable `ScholarlyWork`.

### B. Cache HTTP Persistant sur Disque (`csc.connectors.openalex.cache`)
- `OpenAlexHttpCache` :
  - Clé de cache = SHA-256 de l'URL normalisée.
  - Normalisation : protocole et hôte minusculisés, paramètres de requête triés alphabétiquement, suppression des clés sensibles (`api_key`).
  - Durée de vie configurable (par défaut : 30 jours / 2 592 000 s).
  - Élimination automatique des entrées périmées lors de la lecture.
  - Enregistrement des crédits et métadonnées de réponse.

### C. Limiteur de Débit Token Bucket (`csc.connectors.openalex.rate_limiter`)
- `TokenBucket` : implémentation thread-safe avec capacité maximale et réalimentation progressive en continu.
- `OpenAlexRateLimiter` :
  - 10 req/s (sans clé) ou 30 req/s (avec clé API).
  - 1 req/s pour la recherche sémantique (consomme simultanément sur le seau sémantique et le seau général).
  - Support de `wait=False` pour les tests non bloquants.

### D. Gestionnaire de Budget Journalier (`csc.connectors.openalex.budget`)
- `OpenAlexBudgetManager` :
  - Registre persistant `daily_credits.json` stocké dans `var/cache/openalex/`.
  - Réinitialisation automatique à 0,00 crédit lors du changement de jour (date UTC).
  - Contrôle bloquant préventif avant tout appel réseau : levée de `OpenAlexBudgetExceededError` dès que la consommation atteint ou dépasse 90 % du plafond journalier (90 000 crédits).
  - Réconciliation avec le solde restant `X-RateLimit-Remaining` renvoyé par l'en-tête de l'API.

### E. Client Unifié & Fonctions Exposées (`csc.connectors.openalex.client`, `csc.connectors.openalex`)
Fonctions exposées conformément à la spécification :
```python
search_works(query: str, *, filters: dict | None = None, sort="cited_by_count:desc", per_page=50, max_results=200) -> list[ScholarlyWork]
semantic_search_works(text: str, *, filters: dict | None = None, k=50) -> list[ScholarlyWork]
get_work(id_or_doi: str) -> ScholarlyWork
find_systematic_reviews(topic_query: str, *, since_year=2005) -> list[ScholarlyWork]
top_institutions(topic_id: str, n=3) -> list[Institution]
top_authors(topic_id: str, n=20) -> list[Author]
```
- Pagination transparente par curseur (`cursor=*` puis `cursor=next_cursor`).
- Retries exponentiels sur HTTP 429 et erreurs 5xx avec temporisation respectant `Retry-After`.
- Traçabilité `EvidenceQuery` systématique pour chaque requête exécutée.

### F. Commandes CLI Typer (`backend/src/csc/cli.py`)
- `csc openalex search "carbon tax employment" --reviews-only` : affiche les revues systématiques triées par citations sous forme de tableau Rich.
- `csc openalex search "<query>" [--semantic] [--limit N] [--sort ...]` : recherche générale ou recherche sémantique par similarité conceptuelle.
- `csc openalex get "<doi_or_id>"` : fiche détaillée avec titre, résumé reconstitué, auteurs et métadonnées.
- `csc openalex institutions "<topic_id>" [--limit N]` : top des établissements de recherche.
- `csc openalex authors "<topic_id>" [--limit N]` : top des chercheurs sur le sujet.
- `csc openalex budget` : tableau récapitulatif des crédits consommés, du plafond (1,00 $) et du seuil d'arrêt propre.

### G. Révisions issues de la revue de code
- **Résolution de chemin racine** : utilisation de `_PROJECT_ROOT` depuis `csc.config` dans `OpenAlexHttpCache` et `OpenAlexBudgetManager`, garantissant que les fichiers sont placés dans `var/cache/openalex/` à la racine du dépôt.
- **Sécurisation de l'affichage Rich (crochets & balises scientifiques)** : échappement systématique des entrées utilisateur, titres et auteurs avec `rich.markup.escape`, et affichage des abstracts avec `markup=False` pour éviter tout crash `MarkupError` sur les balises scientifiques (`[95% CI]`, `[/B]`).
- **Normalisation insensible à la casse des DOI** : `get_work` détecte correctement les préfixes `DOI:`, `https://doi.org/` et variantes majuscules.
- **Extraction robuste d'identifiant OpenAlex** : `normalize_openalex_id` extrait le segment terminal canonique quel que soit le format d'entrée (`https://api.openalex.org/works/...`, `topics/...`, etc.).
- **Écriture atomique sur disque** : écriture dans un fichier temporaire puis remplacement atomique (`Path.replace`) pour le cache HTTP et le registre budgétaire.
- **Gestion de connexion Keep-Alive & bornage mémoire** : session HTTP réutilisable sur `OpenAlexClient` avec méthode `close()` et context manager, et limitation de l'historique `recorded_queries` à 1000 entrées avec méthode `clear_recorded_queries()`.

---

## 3. Résultats des Tests et Contrôles Qualité

La cible **`make check` est 100 % verte**, sans avertissement ni contournement :
1. **Formatage Python (`ruff format`)** : 95 fichiers conformes.
2. **Linting Python (`ruff check`)** : 0 erreur, 0 avertissement.
3. **Typage statique strict (`mypy --strict`)** : **0 erreur sur 67 fichiers source**.
4. **Tests Python (`pytest`)** :
   - **146 tests passés avec succès** (2 ignorés réservés aux tests live API Gemini).
   - **49 tests dédiés** au connecteur OpenAlex :
     - Parsing et reconstruction d'abstracts (`test_models.py`).
     - Normalisation robuste des DOI et identifiants (`test_models.py`).
     - Détection des revues systématiques (`test_models.py`).
     - Hachage d'URL, masquage de clé, expiration TTL et résolution de chemin (`test_cache.py`).
     - Token bucket et limitation sémantique 1 req/s (`test_rate_limiter.py`).
     - Compteur de crédits, arrêt propre à 90 % et résolution de chemin (`test_budget.py`).
     - Pagination par curseur, retries 429 / 500, persistance traçabilité, support DOI majuscules et Keep-Alive / éviction (`test_client.py`).
     - Commandes CLI, mode sémantique et tolérance aux balises scientifiques (`test_cli.py`).
5. **Vérification et build du site statique Astro** : 0 erreur, 0 warning, build statique réussi.

---

## 4. Limites et Prochaines Étapes
- Le connecteur est prêt pour l'intégration dans le lot **L10 (Recherche de preuves et SMS)**.
- En production avec une clé API gratuite, renseigner `OPENALEX_API_KEY` et `OPENALEX_EMAIL` dans le fichier `.env` pour bénéficier du pool courtois (*polite pool*) et du débit accru (30 req/s).
