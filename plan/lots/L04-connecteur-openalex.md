# L04 — Connecteur OpenAlex

**Agent** : standard · **Dépend de** : L02 · **Effort** : 1 j
**Fichiers autorisés** : `backend/src/csc/connectors/openalex/`, `backend/tests/connectors/openalex/`

## Contexte (vérifié le 27/10/2026)
- API : `https://api.openalex.org`. **Clé gratuite** recommandée (`api_key=`), obligatoire pour la pagination par curseur au-delà de la première page.
- Budget gratuit : **1 $/jour** par compte. Le coût de chaque requête est renvoyé dans l'en-tête `X-RateLimit-Credits-Used`. Limites : 10 req/s sans clé, 30 avec clé, 50 sur plan annuel. Recherche sémantique limitée à 1 req/s.
- Données sous licence CC0.

## Fonctions à exposer
```python
search_works(query: str, *, filters: dict, sort="cited_by_count:desc", per_page=50, max_results=200) -> list[ScholarlyWork]
semantic_search_works(text: str, *, filters: dict, k=50) -> list[ScholarlyWork]
get_work(id_or_doi: str) -> ScholarlyWork
find_systematic_reviews(topic_query: str, *, since_year=2005) -> list[ScholarlyWork]   # filtre type:review + mots clés meta-analysis / systematic review
top_institutions(topic_id: str, n=3) -> list[Institution]
top_authors(topic_id: str, n=20) -> list[Author]   # utile pour repérer des relecteurs (L00)
```
- Préférer `filter=` à `search=` quand c'est possible (correspondances exactes), comme le recommande le rapport Gemini.
- Reconstituer l'abstract depuis `abstract_inverted_index`.
- **Chaque appel enregistre un `EvidenceQuery`** (URL exacte, paramètres, nombre de résultats, crédits consommés). Ces requêtes sont affichées dans l'onglet « traçabilité » des fiches.

## Exigences
- Cache HTTP persistant (table ou disque, clé = URL normalisée), TTL de 30 jours.
- Limiteur de débit (token bucket) et compteur de crédits journaliers ; arrêt propre à 90 % du budget.
- Retries sur 429 et 5xx avec backoff.

## Critères d'acceptation
- Tests unitaires sur des réponses enregistrées (cassettes) : parsing, reconstruction de l'abstract, pagination, budget.
- CLI : `csc openalex search "carbon tax employment" --reviews-only` affiche 10 résultats triés.
- Aucun appel réseau en CI.
