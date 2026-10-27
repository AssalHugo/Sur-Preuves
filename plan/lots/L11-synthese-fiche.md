# L11 — Synthèse de fiche sourcée

**Agent** : fort · **Phase** : POC · **Dépend de** : L10 · **Effort** : 2 j
**Fichiers autorisés** : `backend/src/csc/pipeline/synthesis/`, `prompts/synthesis_*.md`, `backend/tests/pipeline/synthesis/`, `eval/synthesis/`

## Objectif
Produire un **brouillon de fiche** (`Assessment`, statut `ai_draft`) où chaque phrase est rattachée à des preuves du dossier, avec une qualification nuancée de l'incertitude.

## Structure de la fiche (sortie structurée `Assessment`)
1. **L'affirmation**, citée mot pour mot, avec la source (programme, page).
2. **Ce qui est évalué** et **ce qui ne l'est pas** (part normative explicitement écartée).
3. Pour une affirmation **factuelle** : `FactualVerdict`, valeur citée, valeur de référence, source et date.
4. Pour une affirmation **causale** :
   - mécanisme (théorie du changement) ;
   - état des preuves : `ConsensusLevel`, `EvidenceDirection`, SMS maximal disponible ;
   - ordres de grandeur documentés ;
   - **conditions de réussite** et contexte (pays, période) ;
   - **effets rebonds et effets redistributifs** ;
   - **controverses non tranchées** ;
   - si aucune évaluation ex-post : `novel_no_ex_post` et théorie du changement seulement, **sans conclusion forcée**.
5. **Pluralisme disciplinaire** : sous-sections « environnement / physique », « économie », « sociologie de l'action publique » quand c'est pertinent.
6. **Limites de la fiche**.

## Règles de génération (dans le prompt et contrôlées par du code)
- Le modèle **ne cite que des identifiants `E1…En` du dossier**. Tout identifiant inconnu fait rejeter la sortie et relancer le modèle. **Le modèle n'écrit jamais de DOI lui-même** : le code remplace `E3` par le DOI ou la page au rendu.
- Chaque phrase = un objet `Sentence` avec au moins une citation (sauf phrases de contexte marquées).
- Lexique neutre imposé : pas d'adjectifs évaluatifs (« irréaliste », « démagogique », « courageux »…). Utiliser les formulations du GIEC et de Science Feedback (« les études disponibles suggèrent… », « niveau de confiance moyen »).
- Longueur : résumé ≤ 80 mots (lisible par tous), corps ≤ 600 mots.
- **Même gabarit, même prompt et même règle de choix de modèle pour tous les candidats.** Le nom du candidat **n'est pas transmis** au modèle (évaluation à l'aveugle de l'affirmation).
- **Routage déterministe du modèle**, enregistré dans la fiche :
  - affirmation `causal` → rôle `synthesis` (**Gemini 4 Argon** en batch, réflexion moyenne, `max_output_tokens` ≈ 6k ; repli `gemini-3.1-pro-preview`) ;
  - affirmation `factual` dont la référence est une statistique publique → rôle `synthesis_simple` (**Gemini 3.5 Flash-Lite** en batch).
  - Le LLM ne décide jamais du routage.
- Exécution en **Batch API** par vagues (−50 %), **au fil de la publication des programmes** pour lisser la dépense mensuelle. Avant chaque vague, lancer `csc llm estimate` : la vague est découpée si elle dépasse l'enveloppe restante du mois.
- Pas de cache explicite ; le prompt commence par un préfixe stable (méthode, schéma, exemples) suivi du dossier (cache implicite).

## Critères d'acceptation
- 100 % des phrases non contextuelles ont au moins une citation valide (test automatique).
- Sur 20 fiches de démonstration (programmes 2022), un relecteur expert juge au moins 80 % des fiches « publiables après corrections mineures ».
- Test d'aveugle : le prompt rendu ne contient jamais de nom de candidat ni de parti (test sur le gabarit).
- Coût moyen par fiche ≤ **0,06 $** en novembre 2026 et ≤ **0,12 $** à partir du 1/12/2026 (causale, Argon batch) ; ≤ **0,01 $** (simple, Flash-Lite batch). Mesuré par `csc llm cost`.
- Mise au point des prompts sur l'offre gratuite (Flash-Lite, données publiques), puis validation finale sur le modèle de production.
- **Test A/B du POC** (`eval/synthesis/ab20.jsonl`, 20 affirmations de 2022) :
  - générer chaque fiche avec Gemini 4 Argon et avec Gemini 3.1 Pro (`csc llm ab`) ;
  - présenter les deux versions **anonymisées et dans un ordre aléatoire** au relecteur ;
  - noter l'exactitude, la nuance et la lisibilité, et relever le taux de phrases `supported` selon L12 ;
  - consigner le résultat dans `eval/synthesis/AB_RESULTS.md`.
  - Argon reste par défaut sauf s'il est nettement moins exact.
