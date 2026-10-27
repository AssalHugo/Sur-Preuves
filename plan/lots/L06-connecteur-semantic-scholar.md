# L06 — Connecteur Semantic Scholar (optionnel)

**Agent** : standard · **Dépend de** : L02 · **Effort** : 0,5 j · **Priorité** : basse, phase 2 (à faire seulement si L10 en a besoin)
**Fichiers autorisés** : `backend/src/csc/connectors/s2/`, `backend/tests/connectors/s2/`

## Objectif
Récupérer les **contextes de citation** (« citances ») d'une étude-clé, pour savoir si des travaux ultérieurs l'ont confirmée ou contestée.

## Contexte
API gratuite. Sans clé : quota partagé et faible. Avec une **clé gratuite** (demandée par formulaire) : environ 1 req/s. Prévoir le délai d'obtention de la clé (L00).

## Fonctions à exposer
```python
get_paper(doi: str) -> S2Paper
get_citation_contexts(doi: str, limit=100) -> list[CitationContext]  # {citing_doi, contexts[], intents[], is_influential}
```

## Critères d'acceptation
- Limiteur à 1 req/s, cache, tests sur cassettes.
- Fonction utilitaire `contradiction_signals(doi)` qui compte les contextes contenant des marqueurs de contestation (« failed to replicate », « contrary to », « in contrast »). Ce n'est qu'un indice transmis au relecteur, jamais un verdict.
