# L16 — Déploiement gratuit (Cloudflare Pages), sauvegardes et gel électoral

**Agent** : standard · **Phase** : 3 (publication). **Hors POC** : seule la sauvegarde locale (`make backup`) est nécessaire dès le POC (L01) · **Dépend de** : L14, L15 · **Effort** : 1,5 j

> **Mise à jour (révision 3)** : le back-office ne passe plus par un tunnel. Il sera déployé sur un **hébergement payant** en phase 2 (voir L14). Cloudflare Access ne sert plus qu'à protéger les déploiements de prévisualisation du site. Le site public sur Cloudflare Pages, le formulaire D1 + Turnstile, les sauvegardes et le gel électoral restent valables.
**Fichiers autorisés** : `infra/`, `.github/workflows/deploy*.yml`, `.github/workflows/backup-check.yml`, `web/wrangler.toml`, `web/astro.config.*` (variable de gel uniquement), `Makefile` (cibles `backup*`)

## Infrastructure cible : 0 €/mois
| Élément | Choix | Coût |
|---|---|---|
| Traitements, base, back-office | **PC local** (L01, L14) | 0 € |
| Site public | **Cloudflare Pages** : requêtes statiques illimitées, CDN mondial, anti-DDoS | 0 € |
| Formulaire de rectification | Pages Function + **D1** + **Turnstile** (L15) | 0 € |
| Back-office des relecteurs | Hébergement payant (phase 2, L14), choisi plus tard | ~5 – 10 €/mois |
| Sauvegardes hors site | **Cloudflare R2** (offre gratuite de 10 Go) + disque externe | 0 € |
| CI/CD | GitHub Actions (dépôt public) | 0 € |
| Supervision | Moniteur HTTP gratuit (par exemple UptimeRobot) sur le site public | 0 € |
| Domaine (facultatif) | Recommandé pour la crédibilité du site | ~10 €/an |
| Repli | **GitHub Pages** : limite souple de **100 Go/mois** et site ≤ 1 Go, donc insuffisant lors d'un pic de débat | 0 € |

## Tâches

### 1. Pipeline de publication
1. Sur le PC : `csc publish bundle`, qui écrit `web/src/data/bundle.json`, signé, puis `git commit` et `git push`.
2. **GitHub Actions** (`deploy.yml`), déclenché sur `push` vers `main` ou manuellement :
   1. **étape « gel électoral »** : `python infra/freeze.py check`, qui fait échouer le job si on est dans une fenêtre de gel ;
   2. validation du bundle contre le JSON Schema ;
   3. `npm ci && npm run build` (Astro + Pagefind) ;
   4. test Playwright minimal : aucun cookie posé, aucune requête vers un domaine tiers ;
   5. `npx wrangler pages deploy web/dist --project-name=… --branch=main`.
3. **L'intégration Git native de Cloudflare Pages est désactivée** (mode *Direct Upload*), pour que **seul** le workflow (avec contrôle du gel) puisse déployer.
4. Le jeton Cloudflare (`CLOUDFLARE_API_TOKEN`, droits « Pages : Edit » seulement) n'existe **que** dans les secrets GitHub, pas sur le PC. On ne peut donc pas contourner le gel par un déploiement manuel local.
5. **Déploiements de prévisualisation** (branche `preview`) pour la relecture éditoriale avant mise en ligne. Ils sont protégés par Cloudflare Access.

### 2. Sauvegardes (le PC est un point de défaillance unique)
- `make backup` : `pg_dump -Fc`, chiffrement **age** (clé publique dans `.env`, clé privée hors du PC, sur papier ou gestionnaire de mots de passe), envoi vers **R2** (`rclone` ou `aws s3` compatible) et copie sur le disque externe.
- **Planification quotidienne** (timer systemd ou cron utilisateur) ; rétention de 30 jours quotidiens et de 6 mensuels, dans la limite gratuite de 10 Go.
- Le dossier `var/pdf/` est re-téléchargeable : on sauvegarde seulement son manifeste (URL + SHA-256), pas les fichiers.
- `make restore-test` : restauration dans une base temporaire et comptage des tables. **Exécution mensuelle documentée.**
- Le contenu publié est **aussi** versionné dans Git (bundle), ce qui en fait une seconde sauvegarde indépendante.

### 3. Montée en charge
- Site 100 % statique sur le CDN Cloudflare, sans dépendance au PC. Test k6 contre une URL de prévisualisation : 2 000 req/s sur les pages et les fichiers Pagefind, taux d'erreur nul. Respecter les conditions d'usage de Cloudflare : test court, annoncé dans le README.
- Vérifier la limite de fichiers par déploiement de l'offre gratuite (de l'ordre de 20 000, **à confirmer** dans la doc Cloudflare) par rapport au nombre de fichiers générés (pages + fragments Pagefind) ; alerte en CI au-delà de 80 %.

### 4. Gel électoral (L.49), automatisé
- Fenêtres dans `infra/freeze.yaml` :
  - `2027-04-15T23:59:00+02:00` → `2027-04-18T20:00:00+02:00`
  - `2027-04-29T23:59:00+02:00` → `2027-05-02T20:00:00+02:00`
  - Elles commencent dès le **jeudi**, parce que l'outre-mer et les Amériques votent le samedi. À confirmer par un juriste (L00).
- `infra/freeze.py` : `is_frozen(now) -> bool` et `check` (code de sortie 1 si gel).
- **Le workflow `deploy.yml` échoue** pendant ces fenêtres. Un workflow `freeze-banner.yml` peut déployer **avant** le début du gel une version identique avec un bandeau factuel (« Contenu figé pendant la période électorale »).
- Pendant le gel :
  - le back-office reste utilisable, mais `csc publish bundle` refuse de s'exécuter ;
  - le formulaire de rectification accepte les demandes (stockées dans D1) mais affiche qu'elles seront traitées après le scrutin ;
  - aucune publication sur les réseaux sociaux (procédure humaine dans le runbook).
- Le site reste **accessible en lecture**.

### 5. Sécurité
- En-têtes via `web/public/_headers` : CSP stricte (pas de script tiers), HSTS, `Referrer-Policy: no-referrer`, `Permissions-Policy`.
- Dependabot et `npm audit` / `pip-audit` en CI.
- PC local : pare-feu actif, aucun port entrant ouvert, mises à jour automatiques, disque chiffré (LUKS) recommandé.

### 6. Runbook (`infra/RUNBOOK.md`)
Panne ou perte du PC (restauration depuis R2 sur une autre machine en moins de 2 h) ; retrait d'urgence d'une fiche (republication du bundle précédent, ou `wrangler pages deployment rollback`), avec accord du juriste pendant le gel ; ordonnance en référé (loi de 2018, décision sous 48 h) ; dépassement du budget LLM.

## Critères d'acceptation
- Un push sur `main` hors gel déploie le site sur Cloudflare Pages en moins de 5 minutes ; le même workflow **échoue** quand `FREEZE_NOW` est forcé dans la fenêtre (test de simulation).
- Tests unitaires de `is_frozen()` : bornes incluses et exclues, fuseaux horaires.
- `make backup` produit une archive chiffrée sur R2 ; `make restore-test` réussit.
- Rapport k6 archivé dans `infra/reports/`.
- Le README décrit la création du projet Pages, du jeton à droits minimaux, du bucket R2 et de la base D1, en moins de 20 minutes.
