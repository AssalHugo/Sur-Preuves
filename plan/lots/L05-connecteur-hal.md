# L05 — Connecteur HAL (archive ouverte française)

**Agent** : standard · **Dépend de** : L02 · **Effort** : 0,5 j
**Fichiers autorisés** : `backend/src/csc/connectors/hal/`, `backend/tests/connectors/hal/`

## Contexte (vérifié le 27/10/2026)
- API de recherche Solr : `https://api.archives-ouvertes.fr/search/?wt=json`, sans authentification.
- Le serveur MCP `https://api.archives-ouvertes.fr/mcp` est **expérimental**. Sa documentation prévient de réponses incomplètes ou hallucinées, et il n'expose que des métadonnées. → **Ne pas l'utiliser dans le pipeline de production.** On peut le documenter dans le README comme outil d'exploration manuelle.

## Fonctions à exposer
```python
search(query: str, *, doc_types=("ART","REPORT","THESE","COUV"), since_year=2005, rows=100,
       proximity: tuple[str, str, int] | None = None) -> list[ScholarlyWork]   # ex. '"taxe carbone"~3'
search_by_structure(struct_ids: list[int], query: str) -> list[ScholarlyWork]  # INRAE, IPP, OFCE…
get(hal_id: str) -> ScholarlyWork
```
- Champs `fl=` à demander : `halId_s, doiId_s, title_s, abstract_s, authFullName_s, structName_s, producedDateY_i, docType_s, journalTitle_s, uri_s, fileMain_s`.
- Dédupliquer avec OpenAlex via le DOI (L10 fusionne, mais exposer ici `doi` normalisé en minuscules).
- Enregistrer un `EvidenceQuery` par appel.

## Critères d'acceptation
- Tests sur cassettes : requête de proximité correctement échappée, filtres de type et d'année, parsing.
- Le README liste les identifiants de structures utiles (INRAE, IPP, OFCE, CNRS SHS, Sciences Po LIEPP…), à compléter par un humain.
