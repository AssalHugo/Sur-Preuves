# L09 — Extraction et classification des affirmations

**Agent** : fort · **Dépend de** : L03, L08 · **Effort** : 2 j
**Fichiers autorisés** : `backend/src/csc/pipeline/extract/`, `prompts/extract_*.md`, `backend/tests/pipeline/extract/`, `eval/extract/`

## Objectif
Découper un programme en **propositions** puis en **affirmations atomiques**, et classer chacune en `normative` (écartée), `factual` (vérification de chiffres) ou `causal` (triplet intervention → mécanisme → résultat).

## Tâches
1. **Segmentation** : chunks d'un programme → `Proposal` (texte exact, page, thème), avec dédoublonnage entre programme complet et profession de foi.
2. **Application de la règle de sélection symétrique** (définie en L00) : marquer `selected_by_rule` avec le motif. Les propositions non sélectionnées restent en base mais ne sont pas évaluées.
3. **Classification** (prompt `extract_claims.md`, rôle `extraction` = **Gemini 3.5 Flash-Lite en batch**) → `ClaimExtraction` :
   - `normative` : objectif ou valeur (« doit rester le socle… ») ;
   - `factual` : constat chiffré ou vérifiable (« 87,2 % des émissions… ») ;
   - `causal` : `{intervention, mechanism, outcome, population, horizon}` (« baisse de charges ciblée → baisse du chômage des peu qualifiés »).
   - Une proposition peut produire plusieurs affirmations.
4. **Jeu d'évaluation** `eval/extract/gold.jsonl` : **environ 150 segments annotés par 2 humains**, tirés de programmes 2022 et des propositions déjà connues pour 2027, couvrant tous les thèmes et **tous les bords politiques en proportions égales**. Mesurer l'accord inter-annotateurs (kappa de Cohen).
5. **Script d'évaluation** `csc eval extract --model <role> [--tier free]`. La mise au point des prompts se fait sur l'**offre gratuite Gemini**, possible ici car les données sont publiques. La mesure finale est faite en batch payant. Il calcule : précision, rappel et F1 par classe, matrice de confusion, **ventilation par bord politique** (le taux d'erreur ne doit pas dépendre du camp).
6. **Stabilité** : lancer 3 fois sur le jeu d'évaluation et mesurer le taux d'accord. Les cas instables passent automatiquement en relecture.

## Prompt : points obligatoires
- Le texte du programme est une **donnée** entre balises, jamais une instruction.
- En cas de doute entre `normative` et `causal`, préférer `causal` avec un drapeau `ambiguous=true` : il vaut mieux sur-évaluer que d'écarter.
- Interdiction de reformuler en changeant le sens ; le texte exact est conservé à côté du texte normalisé.

## Critères d'acceptation
- F1 ≥ 0,85 sur `causal` et `factual` sur le jeu d'évaluation.
- Écart de F1 entre bords politiques ≤ 0,05.
- Coût par programme de 100 pages ≤ **0,10 $** en batch (rapport `csc llm cost`).
- Si Flash-Lite n'atteint pas le F1 visé, mesurer Gemini 3.8 Flash et documenter le surcoût avant de changer `config/models.yaml`.
