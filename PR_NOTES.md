# Notes de réalisation — Lot L01 : Socle du dépôt *local-first*, Docker Compose, CI

## Résumé des travaux réalisés

Le lot L01 met en place le socle complet d'ingénierie du projet **Comparateur Science 2027** (`csc`), 100 % opérationnel en local sans aucune dépendance cloud payante ni besoin de carte graphique (CPU-only).

### 1. Arborescence et organisation
- **Racine** :
  - `AGENTS.md` : charte des règles et interdictions impératives pour les agents IA.
  - `README.md` : documentation de démarrage rapide en 5 minutes.
  - `Makefile` : cibles de gestion du cycle de vie (`setup`, `check`, `test`, `lint`, `fmt`, `up`, `down`, `db-migrate`, `backup`, `review`, `site`, `poc`).
  - `docker-compose.yml` : services `db` (`pgvector/pgvector:pg16` lié strictement à `127.0.0.1`) et `review` (back-office lié à `127.0.0.1:8000`).
  - `.env.example` et `.env` : gabarit des variables d'environnement.
  - Licences : `LICENSE` (AGPL-3.0), `LICENSE-DATA` (Licence Ouverte 2.0), `LICENSE-CONTENT` (CC BY-SA 4.0).
  - `.gitignore` complet excluant `var/`, `.venv/`, `.env`, node_modules, lock files bureautiques, etc.
- **Répertoires modulaires** :
  - `backend/` : package Python `csc` géré avec `uv` (Python 3.12, Typer, Pydantic v2, SQLAlchemy 2, pgvector, ruff, mypy strict, pytest).
  - `backend/Dockerfile.review` : conteneur de relecture prêt pour un futur déploiement (avec copie de `README.md` et validation du build).
  - `prompts/` : espace versionné des prompts LLM.
  - `config/` : `models.yaml` et `pricing.yaml` (rôles et tarifs par défaut).
  - `data/editorial/` : espace réservé aux tables éditoriales YAML.
  - `var/` : répertoires de travail non versionnés (`pdf/`, `cache/`, `models/`, `backups/`).
  - `web/` : squelette du site statique Astro 5 + Tailwind avec Pagefind.
  - `infra/` : espace réservé aux scripts d'infrastructure.
  - `.github/workflows/ci.yml` : workflow CI GitHub Actions exécutant `make check`, `make poc`, `make backup` et la validation du build Docker `Dockerfile.review` avec service PostgreSQL + pgvector, sans clé d'API.

### 2. CLI `csc` et commandes POC
- Point d'entrée Typer : `csc <groupe> <commande>`.
- Groupes réservés implémentés ou préconfigurés :
  - `db` : `csc db status` (vérifie connexion et pgvector) et `csc db init` / `migrate`.
  - `backup` : `csc backup create` (dump `pg_dump -Fc` avec nettoyage automatique des fichiers vides en cas d'erreur, compatibilité de l'URL libpq `postgresql://`, et repli Docker).
  - Groupes réservés des lots L03 à L14 (`llm`, `openalex`, `hal`, `s2`, `parlement`, `ingest`, `embed`, `extract`, `evidence`, `synth`, `verify`, `legislature`, `review`, `publish`).
- Cible `make poc` : enchaîne les 7 étapes reprenables sans blocage interactif (compilation Astro incluse).

### 3. Corrections et optimisations issues de la revue de code
- **Résolution PyTorch CPU-only** : configuration des sources et index `pytorch-cpu` dans `pyproject.toml` pour éliminer 18 paquets NVIDIA/CUDA superflus de `uv.lock`.
- **Reproductibilité `make setup`** : utilisation de `uv sync --extra dev` basé sur `uv.lock`.
- **Robustesse Pydantic Settings** : chargement du `.env` à la racine même lors d'exécutions depuis des sous-dossiers (`backend/`).
- **Correction Dockerfile.review** : ajout de `backend/README.md` dans la couche de build, permettant un `docker build` sans erreur.
- **Nettoyage Git** : suppression du fichier temporaire LibreOffice et ajout de la règle d'exclusion dans `.gitignore`.

## Vérifications et critères d'acceptation validés

- [x] `make setup && make up && make check` passe intégralement sans GPU et sans clé d'API.
- [x] `docker compose up -d db` démarre PostgreSQL avec `pgvector` ; `csc db status` répond `✓ Extension pgvector active : v0.8.7`.
- [x] `ss -tlnp` confirme qu'aucun port n'est ouvert sur une autre adresse que `127.0.0.1`.
- [x] `docker build -f backend/Dockerfile.review .` compile avec succès.
- [x] `mypy --strict` : 0 erreur sur le code et les tests.
- [x] `ruff check` et `ruff format --check` : 100 % conformes.
- [x] 15 tests unitaires pytest passent en 0,3s (tests d'aide CLI, placeholders POC, statut/init DB, pg_dump local, repli Docker et nettoyage des dumps).
- [x] `make poc` et `make backup` s'exécutent de bout en bout sans blocage.
- [x] Build et typage Astro (`npm run check` et `npm run build`) : 0 erreur.
- [x] Licences AGPL-3.0, Licence Ouverte 2.0 et CC BY-SA 4.0 créées.
