# L12 — Vérification automatique et contrôle de neutralité

**Agent** : fort · **Phase** : POC · **Dépend de** : L11 · **Effort** : 2 j
**Fichiers autorisés** : `backend/src/csc/pipeline/verify/`, `prompts/verify_*.md`, `backend/tests/pipeline/verify/`, `eval/verify/`

## Objectif
Avant toute relecture humaine, produire un `VerificationReport` qui **signale** les problèmes, pour concentrer le temps de relecture là où c'est utile. Le vérificateur **ne corrige jamais** lui-même.

## Contexte : Gemini seul pour l'instant
Tant qu'un seul fournisseur est utilisé, les erreurs de la synthèse et de la vérification peuvent être corrélées. Parades :
1. **Les contrôles déterministes passent en premier.** Ils sont bloquants et n'utilisent pas de LLM, donc ils ne sont pas concernés par cette corrélation.
2. La vérification LLM utilise un **modèle différent** de celui qui a rédigé la fiche (règle bloquante de L03).
3. La relecture humaine reste obligatoire.
4. Chaque rapport porte `same_provider=true`, ce qui est affiché dans la traçabilité et la méthodologie.

Quand un second fournisseur sera ajouté, ce sera une seule ligne dans `config/models.yaml` plus un adaptateur L03. Ce lot n'a pas à changer.

## Contrôles

| Contrôle | Méthode | LLM ? | Bloquant ? |
|---|---|---|---|
| `doi_resolves` | Requête HEAD sur `https://doi.org/<doi>` et cohérence du titre avec OpenAlex | non | oui |
| `page_anchor` | L'extrait cité figure bien à la page indiquée du document stocké (recherche exacte, puis floue avec `rapidfuzz`) | non | oui |
| `citation_ids` | Toute citation renvoie à un `E1…En` du dossier ; chaque phrase non contextuelle a au moins une citation | non | oui |
| `numbers_match` | Chaque nombre de la fiche apparaît dans un extrait cité, à l'arrondi près (regex + normalisation des formats FR et EN) | non | avertissement |
| `lexicon` | Liste de termes évaluatifs interdits (« irréaliste », « démagogique », « anti-scientifique »…) | non | avertissement |
| `citation_support` | Pour chaque phrase, un **modèle distinct de celui de la synthèse** juge si les extraits cités la soutiennent : `supported`, `partially`, `not_supported`. Par défaut, Gemini 3.5 Flash-Lite vérifie les fiches Argon, et **Gemini 3.1 Flash-Lite** (autre modèle, 0,125 / 0,75 $ en batch) vérifie les fiches rédigées par 3.5 Flash-Lite. Une requête par fiche en batch (~20k tokens) | oui | `not_supported` : oui |
| `tone` | Classifieur du ton (`neutral` / `loaded`), rôle `tone_lint`, Flash-Lite en batch | oui | avertissement |
| `parity` | Statistiques par candidat : nombre de fiches, longueur, répartition des verdicts, taux de drapeaux, **modèle de synthèse utilisé**. Alerte en cas d'écart anormal **dans la méthode** | non | rapport global |
| `stability` | Pour 10 % des fiches (graine publiée), seconde synthèse indépendante (rôle `stability`, Argon) et comparaison des verdicts | oui | avertissement |

## Livrables
- `csc verify run --assessment <id>` et `csc verify batch`.
- `csc verify parity-report` : rapport Markdown ou HTML pour le conseil scientifique.

## Critères d'acceptation
- Jeu `eval/verify/` : 40 phrases avec citations volontairement fausses ou détournées.
  - Les contrôles déterministes détectent 100 % des faux identifiants, faux DOI et fausses pages.
  - `citation_support` détecte au moins 85 % des détournements de sens, avec au plus 15 % de faux positifs.
- La configuration refuse de démarrer si le vérificateur d'une fiche est le même modèle que son rédacteur.
- Chaque `VerificationReport` enregistre `verifier_model` et `same_provider`.
- Coût de vérification ≤ 0,01 $ par fiche.
