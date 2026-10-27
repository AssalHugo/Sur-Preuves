# L14 — Back-office de relecture (local pour le POC, hébergé ensuite)

**Agent** : standard · **Phase** : POC (local) puis phase 2 (hébergé) · **Dépend de** : L02 (développable sur fixtures), branché sur L11 et L12 · **Effort** : 3 j
**Fichiers autorisés** : `backend/src/csc/review/`, `backend/src/csc/publish/`, `backend/tests/review/`, `backend/Dockerfile.review`, `docker-compose.yml` (service `review` uniquement)

## Objectif
Permettre de **valider, corriger ou rejeter** les brouillons IA, avec un historique opposable. C'est la preuve de « relecture humaine substantielle » au sens de l'AI Act (Art. 50(4)).

## Stack
FastAPI + Jinja2 + HTMX + Tailwind, sans framework JS. Conteneur `review` (profil compose `review`), configuré **uniquement par variables d'environnement**, pour être déployable tel quel plus tard.

## Phase POC : local uniquement
- `make review` démarre le back-office sur **`http://127.0.0.1:8000`**, sans aucune exposition réseau.
- Authentification **désactivable** en POC (`REVIEW_AUTH=local`) : un seul utilisateur `admin`, qui est toi. Le code d'authentification complet est quand même écrit et testé, pour la phase 2.
- `noindex` sur toutes les pages.

## Phase 2 : hébergement payant (à faire plus tard, ne pas implémenter le déploiement maintenant)
Préparer seulement ce qui évitera une réécriture :
- **Authentification** : `REVIEW_AUTH=passkey` (WebAuthn) avec **liens d'invitation à usage unique** générés par l'admin (`csc review invite <email>`). Ce mode fonctionne sans service d'envoi d'e-mails.
- **Base** : le back-office ne lit et n'écrit que les tables de relecture (`Assessment`, `Review`, `ChangelogEntry`, `Reviewer`, `RectificationRequest`) et les données nécessaires à l'affichage (preuves, extraits).
  - Prévoir `csc review export-for-hosting` et `csc review import-from-hosting` pour synchroniser la base hébergée avec la base locale. Format : fichiers JSON signés.
  - Les PDF ne sont pas envoyés : seuls les extraits cités le sont.
- Le choix de l'hébergeur (petit VPS UE ou PaaS) se fera à l'ouverture aux chercheurs. Ordre de grandeur : 5 à 10 €/mois. **Ne rien coder de spécifique à un hébergeur.**

## Fonctionnalités (POC)
1. **File de travail** : fiches `ai_draft`, filtrables par thème, par candidat et par drapeau L12.
2. **Vue côte à côte** :
   - la fiche, phrase par phrase ;
   - pour la phrase sélectionnée : les extraits cités (abstract, ou page du PDF stocké en local), les drapeaux L12 et les requêtes `EvidenceQuery` ;
   - le modèle qui a rédigé la fiche, le modèle vérificateur et `same_provider`.
3. **Actions** :
   - approuver ;
   - demander des corrections (commentaire par phrase) ;
   - éditer (diff conservé) ;
   - rejeter ;
   - ajouter une étude par DOI : récupérée via L04, puis requalification SMS **ajoutée à la file de batch**, sans appel en temps réel.
4. **Règles bloquantes** : impossible d'approuver si un contrôle bloquant L12 échoue ou si une phrase n'a plus de citation après édition.
5. **Versioning** : toute modification crée une nouvelle version et une `ChangelogEntry`.
6. **Écran A/B** (POC) : affiche deux versions anonymisées d'une même fiche (Argon / 3.1 Pro, L11), dans un ordre aléatoire, avec une grille de notation. Les résultats sont exportés vers `eval/synthesis/AB_RESULTS.md`.
7. **Export** `csc publish bundle` : `PublicationBundle` (L02) avec les fiches `published`. Option `--include-drafts --poc` pour la démonstration locale.
8. **Tableau de bord** : avancement par candidat et par thème, **budget LLM du mois** (lu depuis L03).

## Fonctionnalités reportées à la phase 2
Rôles multiples et validation finale par l'`editor`, affectation automatique avec gestion des conflits d'intérêts, double relecture, import des demandes de rectification.

## Données personnelles
POC : aucune, puisque tu es le seul utilisateur. Phase 2 : minimisation (nom public, e-mail, ORCID, déclaration d'intérêts), mention RGPD.

## Critères d'acceptation (POC)
- Test de bout en bout (Playwright, en local) : approbation, demande de corrections, édition, puis export du bundle.
- Test : impossible d'approuver une fiche avec un drapeau bloquant.
- Test : en mode `passkey`, une route protégée sans session renvoie 401, et un lien d'invitation ne marche qu'une fois.
- `docker compose --profile review up` fonctionne ; le conteneur n'écoute que sur `127.0.0.1`.
