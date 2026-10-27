# L00 — Gouvernance, neutralité et cadre juridique

**Type** : lot humain, en continu ; une IA peut rédiger les brouillons · **Dépend de** : — · **Échéance critique** : 8 novembre 2026 pour la charte, 10 janvier 2027 pour les 20 relecteurs

## Objectif
Construire la confiance avant le code. Sans structure indépendante, sans charte et sans relecteurs, la plateforme ne pourra pas publier.

## Tâches
1. **Structure porteuse** : association loi 1901 (ou rattachement à une structure existante). Statuts avec une clause d'indépendance : aucun dirigeant engagé dans une équipe de campagne ou titulaire d'un mandat partisan. Rappel : en 2017, le cas Voxe / Hamon a montré que cette indépendance est vitale.
2. **Financement transparent** : publier la liste des financeurs ; refuser tout financement d'un parti ou d'un candidat ; ne jamais acheter de publicité à visée électorale (L.52-1, en vigueur depuis le 1er octobre 2026).
3. **Charte de neutralité et de méthode** (publique), qui fixe :
   - aucune note globale et aucun classement des candidats ; ordre alphabétique ou aléatoire ;
   - une **règle de sélection symétrique** des propositions évaluées, avec **20 à 25 propositions par candidat** (même nombre pour tous). Proposition : d'abord les mesures chiffrées ou causales des **professions de foi officielles (FALC)**, puis, pour compléter, celles du programme complet selon des **critères objectifs et publiés** (mesure chiffrée, impact budgétaire déclaré, répartition entre thèmes). **Ne pas sélectionner « les plus clivantes »** : ce critère est subjectif et exposerait le site à une accusation de biais ;
   - la séparation du normatif (non évalué) et du positif (évalué) ;
   - les échelles : SMS 1 à 5, niveaux de consensus ;
   - la procédure de rectification et le droit de réponse, avec délai de réponse.
4. **Conseil scientifique** (5 à 9 personnes, disciplines variées : économie, climat et énergie, santé, sociologie, droit), avec déclarations d'intérêts publiques.
5. **Recrutement des relecteurs** (environ 330 heures de relecture à répartir) : au moins 20 chercheurs titulaires d'un doctorat et publiants (repérés via OpenAlex et HAL), avec déclaration d'intérêts. Prendre contact avec Science Feedback, les laboratoires, l'IPP, l'OFCE et l'I4CE pour d'éventuels partenariats.
6. **Conseil juridique sans budget** : clinique juridique universitaire, avocat pro bono ou association spécialisée (droit électoral, AI Act, RGPD). Faire valider
   - les fenêtres de gel autour des 18 avril et 2 mai 2027, en tenant compte du **vote du samedi outre-mer** ;
   - l'auto-évaluation AI Act au titre de l'Art. 6(3)/6(4) et la mention IA de l'Art. 50 ;
   - le traitement des données des relecteurs et du formulaire de contact (RGPD) ;
   - la conformité TDM (CPI L.122-5-3) du scraping des sites de campagne.
7. **Désigner un responsable éditorial** (personne physique), au titre de l'exception de l'Art. 50(4) et de la loi de 1881.

## Livrables (dans `docs/gouvernance/`)
`charte-neutralite.md`, `regle-selection-propositions.md`, `conseil-scientifique.md`, `declarations-interets/`, `procedure-rectification.md`, `avis-juridique.md` (synthèse), `financeurs.md`.

## Critères d'acceptation
- La charte et la règle de sélection sont publiées **avant** l'ingestion du premier programme.
- 20 relecteurs ou plus sont engagés au 10 janvier 2027, avec une couverture de chaque thème par au moins 2 relecteurs ; les créneaux de relecture (back-office local, L14) sont communiqués.
- L'avis juridique est reçu avant l'ouverture publique.
