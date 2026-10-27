# L17 — Méthodologie publique et documents de conformité

**Agent** : standard (rédaction), puis validation par le juriste (clinique juridique ou pro bono) et le conseil scientifique · **Dépend de** : L11 (méthode stabilisée), L00 · **Effort** : 1 j
**Fichiers autorisés** : `docs/`, `web/src/content/` (pages éditoriales)

## Livrables
1. **`docs/methodologie.md`** → page `/methodologie/` :
   - ce qui est évalué (faits, mécanismes causaux) et ce qui ne l'est pas (valeurs, objectifs) ;
   - la règle de sélection des propositions (L00) ;
   - l'échelle SMS (tableau 1 à 5 avec exemples) et les niveaux de consensus ;
   - le pipeline, schéma inclus : extraction → recherche → synthèse → vérification croisée → relecture → publication ;
   - les modèles d'IA utilisés (fournisseur, version, rôle), et le lien vers `prompts/` dans le dépôt public ;
   - **si la vérification utilise encore le même fournisseur que la synthèse** (Gemini) : le dire explicitement, puis expliquer les parades (modèle différent, contrôles déterministes, relecture humaine) ;
   - les limites connues (biais de publication, littérature surtout anglo-saxonne, mesures inédites).
2. **`docs/conformite/ai-act.md`** : auto-évaluation
   - pourquoi le système n'est pas « destiné à influencer le vote » (Annexe III, point 8(b)) : aucun profilage, aucun classement, aucune recommandation, la recherche documentaire prime, relecture humaine, indépendance ;
   - documentation au titre de l'Art. 6(3) et 6(4) et préparation de l'enregistrement de l'Art. 49(2) si le juriste le juge nécessaire ;
   - Art. 50 : mention IA et marquage lisible par machine (L15) ; journal de relecture (L14) au titre de l'exception de l'Art. 50(4) ;
   - rappel : les obligations « haut risque » de l'Annexe III s'appliquent à partir du **2 décembre 2027** (Règlement 2026/1744) ; prévoir la revue de conformité **avant** cette date si le site continue.
3. **`docs/conformite/rgpd.md`** : registre des traitements (relecteurs, formulaire de rectification, journaux à durée courte) ; **aucun traitement d'opinions politiques des visiteurs** ; base légale, durées, droits.
   - **Sous-traitants** : Cloudflare (Pages, D1, Turnstile, R2), GitHub, Google (API Gemini payante, sans réutilisation des données), l'hébergeur du back-office (phase 2). Préciser les transferts hors UE et leurs garanties (DPA, cadre UE–États-Unis).
   - Les sauvegardes sur R2 sont **chiffrées avant envoi**.
   - L'offre gratuite Gemini n'est utilisée que pour des données publiques.
4. **`docs/conformite/droit-electoral.md`** : L.52-1 (aucune publicité payante, période en cours depuis le 1er octobre 2026), L.52-8 (aucun avantage à un candidat : égalité de traitement documentée), L.49 (gel, renvoi vers L16), loi du 22 décembre 2018 (traçabilité des sources, procédure de retrait).
5. **`docs/conformite/tdm-cpi.md`** : politique de fouille de textes (L.122-5-3 III), respect des oppositions, conservation sécurisée, réponse aux ayants droit ; droit de courte citation pour l'affichage.
6. **Pages légales** : mentions légales, déclaration d'accessibilité, politique de confidentialité, page « Financement ».

## Critères d'acceptation
- Chaque affirmation des pages de conformité renvoie à un article de loi ou à une décision.
- Relu et validé (trace écrite) par le juriste et par au moins 2 membres du conseil scientifique avant l'ouverture publique.
