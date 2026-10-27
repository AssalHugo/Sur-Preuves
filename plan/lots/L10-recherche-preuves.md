# L10 — Recherche de preuves et qualification SMS

**Agent** : fort · **Dépend de** : L04, L05, L08, L09 (L06 optionnel) · **Effort** : 2 j
**Fichiers autorisés** : `backend/src/csc/pipeline/evidence/`, `prompts/evidence_*.md`, `backend/tests/pipeline/evidence/`, `eval/evidence/`

## Objectif
Pour chaque affirmation `causal` ou `factual`, constituer un **dossier de preuves** traçable : études classées par qualité méthodologique, extraits de rapports institutionnels ancrés à la page et requêtes exactes conservées.

## Étapes
1. **Planification des requêtes** (rôle `query_planning`, Gemini 3.5 Flash-Lite en batch) : à partir du triplet causal, produire 3 à 6 requêtes **en anglais et en français** (synonymes, termes techniques comme « payroll tax cut low-wage employment »), plus des filtres OpenAlex (topics, type `review`, années).
2. **Collecte** en parallèle :
   - OpenAlex (L04) : `search_works`, `find_systematic_reviews`, `semantic_search_works` ;
   - HAL (L05) : `search` et `search_by_structure` (IPP, OFCE, INRAE…) ;
   - corpus institutionnel (L08) : `search_chunks`.
3. **Fusion et dédoublonnage** par DOI, puis par titre normalisé. Score = pertinence sémantique × qualité × log(citations), en **bonifiant les revues systématiques et méta-analyses**.
4. **Qualification méthodologique, en deux temps pour économiser** :
   - **(a) heuristiques déterministes gratuites** sur l'abstract et le type OpenAlex : mots-clés « randomized », « difference-in-differences », « regression discontinuity », « meta-analysis », « systematic review »… Elles donnent un `design` et un SMS provisoire ;
   - **(b) LLM** (rôle `sms_grading`, Flash-Lite en batch) **seulement pour les 30 meilleures études après dédoublonnage**. Il produit `design`, `sms_level` 1 à 5 et une justification courte. Un désaccord entre heuristique et LLM lève un drapeau.
5. **Filtrage** : on garde les études de niveau SMS ≥ 3 et les revues systématiques. Les niveaux 1–2 sont conservés à part, pour mentionner l'absence de preuves solides si c'est le cas. Pour une affirmation `factual`, on priorise la statistique publique (INSEE, SDES, DREES…) et les rapports institutionnels.
6. **Dossier de preuves compact** : liste numérotée `E1…En` d'`EvidenceItem`, chacun avec l'extrait exact (abstract ou passage avec page), la direction pressentie et le niveau SMS.
   - **Taille ≤ 25k tokens**, soit environ 12 à 15 études et 5 à 8 extraits institutionnels, choisis par le score de l'étape 3.
   - Les études écartées restent consultables par le relecteur dans L14, qui peut en réintégrer.
   - Le dossier est rendu **après** le préfixe stable du prompt (cache implicite, voir L03).
7. **Traçabilité** : toutes les `EvidenceQuery` sont liées à l'affirmation (affichage public).

## Critères d'acceptation
- Jeu d'évaluation `eval/evidence/` : 30 affirmations avec les études-clés attendues désignées par un expert. Rappel@20 ≥ 0,7.
- Accord SMS LLM / expert (à ±1 niveau) ≥ 80 % sur 50 abstracts annotés.
- Aucune étude sans DOI ni identifiant HAL ou OpenAlex dans un dossier.
- Coût LLM moyen ≤ 0,01 $ par affirmation ; consommation OpenAlex dans l'enveloppe gratuite de 1 $/jour (cache).
