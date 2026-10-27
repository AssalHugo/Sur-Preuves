# L15 — Site public statique

**Agent** : standard (lot qui gagne à passer par une étape de design dédiée) · **Dépend de** : L02 (fixtures), branché sur L14 · **Effort** : 3 j
**Fichiers autorisés** : `web/` (y compris `web/functions/` pour la Pages Function)
**Phase** : POC (local) → phase 3 (en ligne)
**Hébergement** : POC : `npm run build && npm run preview` sur `127.0.0.1:4321`. Phase 3 : **Cloudflare Pages** (0 €), déploiement par L16
**POC** : pages candidats, thèmes, fiches avec onglets « Traçabilité » et « Historique », méthodologie provisoire, bandeau « POC — fiches non relues » quand le bundle est en mode `--poc`. Le formulaire de rectification (Pages Function) est reporté à la phase 3.

## Objectif
Un site **rapide, accessible, sans cookie et sans compte**, généré à partir du `PublicationBundle`, qui présente les candidats **à égalité**.

## Stack
Astro 5 (`output: 'static'`), Tailwind, **Pagefind** pour la recherche plein texte côté client, TypeScript strict. Types générés depuis `web/src/schema/bundle.schema.json` (L02).

## Pages
| Route | Contenu |
|---|---|
| `/` | Explication en 3 phrases de ce que fait et ne fait pas le site ; accès par **thème** et par **candidat** |
| `/candidats/` | Liste dans un **ordre aléatoire tiré côté client** à chaque visite (sans stockage), avec un bouton « ordre alphabétique » |
| `/candidats/[slug]/` | Propositions évaluées, groupées par thème ; lien vers le programme source |
| `/themes/[theme]/` | Les propositions de tous les candidats sur le thème, côte à côte |
| `/fiches/[id]/` | La fiche : résumé, verdict ou consensus (avec pictogrammes **non colorés rouge/vert**), corps, sources numérotées (DOI cliquables), onglets **« Traçabilité »** (requêtes exactes, modèles, versions de prompts, relecteurs, dates) et **« Historique »** (changelog) |
| `/legislature/` | Module L13 |
| `/comparer/` | Comparateur : propositions épinglées par l'utilisateur, **stockées uniquement en `localStorage`**, avec try/catch si le stockage est indisponible |
| `/methodologie/`, `/charte/`, `/qui-sommes-nous/`, `/financement/`, `/corrections/` | Contenus de L00 et L17 |
| `/donnees/` | Téléchargement du bundle JSON et lien vers le dépôt et les prompts |

## Règles impératives
- **Aucune note globale, aucun classement, aucun questionnaire de profilage.** C'est la frontière de l'AI Act (Art. 6(3)) et du RGPD.
- **Aucun cookie, aucun traceur, aucune police ni script tiers.** Polices auto-hébergées. Pas d'analytics, ou alors uniquement des compteurs agrégés côté CDN sans IP.
- **Mention IA** (Art. 50) sur chaque fiche : « Brouillon rédigé avec l'assistance d'outils d'IA, vérifié et validé par [relecteurs], sous la responsabilité éditoriale de [nom] ». Ajouter une métadonnée lisible par machine : `<meta name="ai-assisted" content="true">`, un champ `aiAssisted` dans le JSON-LD et les métadonnées IPTC `digitalSourceType` adaptées.
- **Accessibilité RGAA / WCAG 2.2 AA** : contrastes, navigation clavier, `prefers-reduced-motion`, textes alternatifs, mode sombre. Résumés écrits en langage clair (inspiré du FALC).
- Responsive dès 320 px, sans défilement horizontal.
- Formulaire « signaler une erreur / proposer une étude » : seul point dynamique.
  - **Pages Function** `web/functions/api/rectification.ts`, avec contrôle **Turnstile** (anti-robot de Cloudflare, gratuit, sans cookie de pistage) et validation du schéma ;
  - écriture dans **Cloudflare D1**, avec limitation de débit ;
  - aucune dépendance au PC local, donc fonctionne même quand il est éteint. L14 rapatrie puis purge les demandes ;
  - données minimales (motif, DOI, e-mail facultatif) et mention RGPD.
  - Si le repli GitHub Pages est utilisé (pas de Functions) : lien `mailto:` vers une adresse dédiée.
- **Bandeau de gel électoral** piloté par une variable de build (L16).

## Critères d'acceptation
- `npm run build` génère le site depuis les fixtures L02 ; Lighthouse ≥ 95 en performance et accessibilité sur `/fiches/[id]`.
- Test Playwright : aucun cookie posé, aucune requête vers un domaine tiers.
- Test : l'ordre des candidats change entre deux chargements et la vue alphabétique est stable.
- Validation axe-core sans erreur sérieuse.
- Test de la Pages Function en local (`wrangler pages dev` avec une base D1 locale) : jeton Turnstile invalide → 403 ; charge utile valide → ligne insérée.
- Le site construit tient dans les limites gratuites de Cloudflare Pages (nombre et taille des fichiers vérifiés en CI par L16).
