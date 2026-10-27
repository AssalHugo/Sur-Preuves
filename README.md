# Comparateur Programmes politiques 2027 × État de la science (`csc`)

> **Projet civique et scientifique d'évaluation factuelle et causale des programmes politiques de l'élection présidentielle 2027.**
> Ce dépôt fonctionne selon le principe **local-first** : l'intégralité du traitement s'exécute sur une machine locale standard (CPU uniquement, sans GPU ni service cloud payant).

---

## Principes clés

1. **Aucune note globale, aucun classement de candidat** : seules les affirmations factuelles et les mécanismes de causalité sont évalués au regard de la littérature scientifique évaluée par les pairs (SMS 1 à 5).
2. **Local-first strict** : base PostgreSQL 16 + `pgvector` en conteneur Docker isolé, CLI `csc` en Python 3.12 (`uv`), embeddings locaux (`fastembed`).
3. **Sécurité et réseau** : tous les services locaux écoutent exclusivement sur `127.0.0.1`. Aucun service payant en ligne ni tunnel n'est utilisé pour le POC.
4. **Zéro profilage & Respect RGPD** : aucun cookie, aucun suivi, aucun compte visiteur. Le site public est 100 % statique (Astro).

---

## Démarrage en 5 minutes (en local)

### Prérequis

- [Docker](https://docs.docker.com/engine/install/) et Docker Compose v2+
- [uv](https://docs.astral.sh/uv/) (gestionnaire de paquets Python ultra-rapide) :
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [Node.js](https://nodejs.org/) v20+ ou v22+ et `npm`
- `make`

### Installation & Lancement

1. **Cloner le dépôt et initialiser l'environnement :**
   ```bash
   cp .env.example .env
   make setup
   ```
   *`make setup` installe les dépendances Python dans un environnement virtuel géré par `uv`, installe les dépendances npm du site Astro et prépare l'arborescence `var/`.*

2. **Démarrer la base de données locale (PostgreSQL + pgvector) :**
   ```bash
   make up
   make db-migrate
   ```

3. **Vérifier l'état de la base de données :**
   ```bash
   uv run csc db status
   ```
   *Doit afficher : `✓ Connecté avec succès` et `✓ Extension pgvector active`.*

4. **Lancer la suite de vérifications complète :**
   ```bash
   make check
   ```
   *Exécute le linting (`ruff`), le typage strict (`mypy --strict`), les tests unitaires (`pytest`) et la compilation du site Astro sans clé d'API requise.*

5. **Exécuter le squelette de pipeline POC :**
   ```bash
   make poc
   ```

---

## Commandes Make disponibles

| Commande | Action |
|---|---|
| `make setup` | Prépare `.env`, les répertoires `var/`, installe Python (`uv`) et Web (`npm`) |
| `make up` | Démarre le conteneur PostgreSQL + pgvector (`127.0.0.1:5432`) |
| `make down` | Arrête les conteneurs Docker |
| `make check` | Vérification complète : linter, typage strict, tests backend et site Astro |
| `make test` | Lance la suite de tests unitaires avec `pytest` |
| `make lint` | Analyse statique du code (`ruff check`, `mypy --strict`, `astro check`) |
| `make fmt` | Formate automatiquement le code Python (`ruff format`) |
| `make db-migrate` | Active l'extension `vector` et applique les migrations |
| `make backup` | Exporte un dump PostgreSQL compressé (`pg_dump -Fc`) vers `var/backups/` |
| `make review` | Démarre le conteneur du back-office de relecture sur `http://127.0.0.1:8000` |
| `make site` | Compile et sert le site statique Astro sur `http://127.0.0.1:4321` |
| `make poc` | Enchaîne les étapes reprenables du pipeline POC |

---

## Arborescence du projet

```
comparateur-science-2027/
├── AGENTS.md                 # Règles impératives pour les agents d'assistance IA
├── README.md                 # Guide de démarrage rapide
├── Makefile                  # Cibles de développement (setup, check, up, poc...)
├── docker-compose.yml        # Services Docker locaux (db pgvector, review)
├── .env.example              # Variables d'environnement documentées
├── backend/                  # Application Python et package `csc`
│   ├── pyproject.toml        # Configuration uv, dépendances, ruff, mypy
│   ├── src/csc/              # Code source du package csc
│   │   ├── cli.py            # Point d'entrée Typer : `csc <groupe> <commande>`
│   │   ├── config.py         # Paramètres Pydantic Settings
│   │   └── db.py             # Connexion SQLAlchemy et gestion pgvector
│   ├── tests/                # Tests unitaires et d'intégration
│   └── Dockerfile.review     # Image de déploiement pour le back-office
├── prompts/                  # Prompts versionnés et tracés
├── config/                   # Configuration des modèles (models.yaml) et coûts (pricing.yaml)
├── data/editorial/           # Tables éditoriales YAML (candidats, partis, correspondances)
├── var/                      # Données de travail NON versionnées (pdf/, cache/, models/, backups/)
├── web/                      # Site public statique Astro 5 + Tailwind
├── infra/                    # Scripts d'infrastructure, gel électoral et déploiement
└── .github/workflows/ci.yml  # Intégration continue GitHub Actions
```

---

## Licences

- **Code source** : [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE)
- **Données publiques et métadonnées** : [Licence Ouverte 2.0 (Etalab)](LICENSE-DATA)
- **Contenus éditoriaux et synthèses** : [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](LICENSE-CONTENT)
