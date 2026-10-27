# L13 — Module « bilan scientifique de la législature »

**Agent** : standard · **Phase** : 2 (le POC teste seulement 2 textes via L07) · **Dépend de** : L07, L11, L12 · **Effort** : 1,5 j · **Budget** : environ 30 fiches, soit ~4 $ de LLM (janvier 2027)
**Fichiers autorisés** : `backend/src/csc/pipeline/legislature/`, `data/editorial/textes_legislature.yaml`, `prompts/legislature_*.md`, `backend/tests/pipeline/legislature/`

## Objectif
Avant même la publication des programmes (février 2027), montrer comment les **groupes parlementaires sortants** ont voté sur **10 grands textes** (périmètre réduit pour le budget ; extensible plus tard) dont un volet relève de l'état des connaissances (climat, énergie, santé, retraites, fiscalité, agriculture…). C'est le premier contenu public et il est disponible tôt.

## Tâches
1. **Sélection des textes** (`textes_legislature.yaml`), **par le conseil scientifique (L00)** avec un critère publié, par exemple « textes ayant fait l'objet d'une évaluation par une institution indépendante : HCC, Cour des comptes, IPP, OFCE… ».
2. Pour chaque texte, identifier les **articles et amendements à composante scientifique** (classification LLM des exposés des motifs, avec le même pipeline que L09), puis réaliser les fiches scientifiques correspondantes avec L10 et L11.
3. **Positions des groupes** (L07), présentées en trois niveaux :
   - vote solennel sur l'ensemble ;
   - votes sur les articles ou amendements évalués ;
   - amendements déposés par le groupe sur ces points.
4. **Présentation sans jugement** : on juxtapose « ce que disent les preuves » et « comment chaque groupe a voté ». On n'écrit **jamais** « le groupe X a voté contre la science » : un vote mêle légitimement des arbitrages normatifs.
5. **Égalité de traitement** : un candidat sans groupe parlementaire obtient une mention explicite et identique (« pas de groupe à l'Assemblée sur la XVIIe législature ») ; aucun contenu de substitution.

## Critères d'acceptation
- Pour chaque scrutin affiché, l'identifiant officiel (`VTANR5L17V…`) est cliquable vers le site de l'Assemblée.
- Test : aucune chaîne de type « vote contre la science », « anti-scientifique » ne peut être générée (lint L12).
- Le bundle de publication (L02) intègre une section `legislature` validée contre le schéma.
