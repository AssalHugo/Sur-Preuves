# L01 — Socle du dépôt *local-first*, Docker Compose, CI

**Agent** : standard · **Phase** : POC · **Dépend de** : — · **Effort** : 0,5 j

## Objectif
Créer un dépôt où **tout tourne sur le PC local** (CPU, sans GPU) avec `docker compose` et une CLI `csc`, et où n'importe quel agent IA peut réaliser un lot en isolation. Point d'entrée unique de vérification : `make check`. **Aucun service cloud payant.**

## Arborescence à créer
```
comparateur-science-2027/
├── AGENTS.md                 # règles pour agents IA (voir ci-dessous)
├── README.md                 # « démarrer en 5 minutes » en local
├── Makefile                  # setup, check, test, lint, fmt, up, down, db-migrate, backup, review, site, poc
├── docker-compose.yml        # profils : core (postgres+pgvector), review (back-office)
├── .env.example              # GEMINI_API_KEY, GEMINI_FREE_API_KEY (facultatif), OPENALEX_API_KEY,
│                             # NOSPARLEMENTAIRES_API_KEY, DATABASE_URL, LLM_MONTHLY_CAP_USD=9,
│                             # BACKUP_DIR (disque externe)
├── backend/
│   ├── pyproject.toml        # package `csc` (uv) ; extras : [ingest] docling, [embed] fastembed
│   ├── src/csc/__init__.py
│   ├── src/csc/cli.py        # point d'entrée Typer : `csc <groupe> <commande>`
│   └── tests/
├── prompts/                  # prompts versionnés
├── config/                   # models.yaml, pricing.yaml (L03)
├── data/editorial/           # tables éditoriales YAML
├── var/                      # NON versionné : pdf/, cache/, models/ (poids ONNX), backups/
├── web/                      # site Astro (L15)
├── infra/                    # L16 : workflows de déploiement, gel, sauvegardes
├── docs/
└── .github/workflows/ci.yml  # make check sur chaque PR (backend + web), sans clé d'API
```

## `docker-compose.yml` (exigences)
- Service `db` : `pgvector/pgvector:pg16`, volume nommé `pgdata`, port **lié à `127.0.0.1:5432` uniquement**, healthcheck, `shared_buffers` et `work_mem` adaptés (variables).
- Service `review` (profil `review`) : image du back-office (L14), **lié à `127.0.0.1:8000`**. Le `Dockerfile` est écrit pour pouvoir être déployé tel quel plus tard sur un hébergement payant (configuration par variables d'environnement uniquement, aucun chemin local en dur).
- **Pas de tunnel ni de service cloud** dans le POC.
- Le pipeline et les connecteurs tournent **sur l'hôte** via `uv run csc …`, pour profiter de tous les cœurs CPU sans surcoût de virtualisation. Ils peuvent aussi tourner dans un conteneur `worker` optionnel.
- Aucune dépendance CUDA : épingler les roues CPU de `onnxruntime` et `torch` (si Docling en a besoin) pour éviter de télécharger des binaires GPU de plusieurs Go.

## CLI `csc` : groupes réservés (implémentés par les lots suivants)
`db`, `llm` (L03), `openalex` (L04), `hal` (L05), `s2` (L06), `parlement` (L07), `ingest` / `embed` (L08), `extract` (L09), `evidence` (L10), `synth` (L11), `verify` (L12), `legislature` (L13), `review` / `publish` (L14), `backup` (L16). L01 crée le squelette avec `csc --help` et `csc db status`.

## Cible `make poc` (squelette créé ici, complétée au fil des lots)
Elle enchaîne les étapes du POC (PLAN.md §8.1) sur le corpus de 2022 :
1. `csc ingest` ;
2. `csc extract` ;
3. `csc evidence` ;
4. `csc synth` (soumission puis collecte des batchs) ;
5. `csc verify` ;
6. `csc publish bundle --include-drafts --poc` : les brouillons sont inclus, marqués « POC, non relu », **jamais déployable** ;
7. `make site`, qui sert le site sur `127.0.0.1:4321`.

Chaque étape est reprenable. Tant qu'un lot n'est pas livré, son étape affiche « non implémentée » au lieu d'échouer.

`make backup` fait un `pg_dump -Fc` vers `BACKUP_DIR` dès le POC.

## Contenu d'`AGENTS.md`
- Lire `plan/PLAN.md` et le fichier du lot avant toute action ; un lot = une PR.
- **Local-first** : tout traitement s'exécute en local ; n'introduire **aucun service cloud payant** ni dépendance GPU.
- **LLM : Gemini uniquement** pour l'instant, via `csc.llm`. Ne pas ajouter d'autre SDK de fournisseur.
- Python 3.12, `uv`, Pydantic v2, SQLAlchemy 2, `mypy --strict`, `ruff`.
- **Interdits** : modifier `backend/src/csc/contracts/` sans validation humaine ; committer des clés ou le dossier `var/` ; faire des appels réseau dans les tests (utiliser des cassettes, `respx` ou `pytest-recording`) ; appeler un LLM hors de `csc.llm` ; utiliser l'API LLM payante pendant le développement (utiliser `FakeProvider` ou l'offre gratuite Gemini, avec des données publiques uniquement) ; collecter des données de visiteurs.
- Les traitements longs sont **reprenables** (idempotents, avec reprise sur erreur) et affichent une barre de progression.
- Langue : code en anglais, contenus éditoriaux et docs en français.
- Fin de lot : `make check` vert, plus `PR_NOTES.md`.

## Critères d'acceptation
- Sur une machine vierge avec Docker : `make setup && make up && make check` passe sans GPU et sans clé d'API.
- `make up` démarre Postgres avec l'extension `vector` ; `csc db status` répond.
- `ss -tlnp` ne montre aucun port du projet ouvert sur une autre adresse que `127.0.0.1`.
- CI GitHub Actions verte sur une PR de test ; dépôt **public**, donc minutes de CI gratuites.
- Fichiers `LICENSE` (AGPL-3.0), `LICENSE-DATA` (Licence Ouverte 2.0) et `LICENSE-CONTENT` (CC BY-SA 4.0) présents.

## Hors périmètre
Le contenu métier, l'hébergement du back-office (phase 2) et le déploiement du site (L16, phase 3).
