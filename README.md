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

## Couche LLM & Plafond budgétaire strict (Lot L03)

Le projet utilise exclusivement l'API Gemini (`google-genai`) avec des règles strictes d'économie et d'audit :
- **Batch API obligatoire par défaut** pour le palier payant (-50 % sur les tarifs d'inférence).
- **Double plafond mensuel** :
  1. **Plafond logiciel interne** (`LLM_MONTHLY_CAP_USD`, par défaut **9,00 $/mois**) : vérifié **avant** chaque envoi d'inférence (`BudgetExceededError`), avec découpage automatique des batches si nécessaire.
  2. **Filet de sécurité Google AI Studio (*Project Spend Cap*) réglé à 10 $/mois** par l'humain.

### Procédure de configuration du *Project Spend Cap* (Google AI Studio / GCP) :
1. Se connecter sur la console [Google Cloud Platform / AI Studio](https://aistudio.google.com/).
2. Accéder à **Facturation / Budgets et alertes** (*Billing & Budgets*).
3. Définir un plafond de dépense mensuel strict (*Spend Cap*) de **10,00 $ USD** pour le projet associé à `GEMINI_API_KEY`.
4. Configurer des alertes par e-mail à 50 %, 80 % et 100 % de l'enveloppe budgétaire.

### Commandes CLI LLM :
- `uv run csc llm budget` : affiche le budget consommé ce mois, le restant, la projection et le détail par rôle/modèle.
- `uv run csc llm cost --since YYYY-MM-DD` : affiche le journal d'audit des dépenses depuis une date.
- `uv run csc llm estimate <prompt_id> --items-count N` : simule le coût et les tokens d'un traitement sans appel réseau.
- `uv run csc llm ab --role synthesis --models gemini-4-argon,gemini-3.1-pro-preview` : prépare l'évaluation A/B à l'aveugle.

---

## Connecteur HAL — Archive ouverte nationale (Lot L05)

Le connecteur interroge l'API Solr de HAL (`https://api.archives-ouvertes.fr/search/?wt=json`) sans authentification, avec mise en cache disque (TTL 30 jours dans `var/cache/hal/`) et traçabilité systématique des requêtes (`EvidenceQuery`).
*Note sur le serveur MCP HAL (`https://api.archives-ouvertes.fr/mcp`) : ce point d'accès est expérimental et non retenu dans le pipeline automatique, mais utilisable manuellement pour l'exploration.*

### Identifiants AuréHAL de structures de recherche utiles (`structId_i`) :

| Acronyme | Identifiant `structId_i` | Organisme de rattachement | Domaine clé |
|---|---|---|---|
| **IPP** | `266522` | Institut des Politiques Publiques | Évaluation micro-économique des politiques publiques |
| **OFCE** | `250936` | Observatoire français des conjonctures économiques (Sciences Po) | Macroéconomie, fiscalité carbone, politiques publiques |
| **INRAE** | `577435` | Institut National de Recherche pour l’Agriculture, l’Alimentation et l’Environnement | Agriculture, climat, ressources naturelles et biodiversité |
| **CNRS-SHS** | `84039` | Institut des Sciences Humaines et Sociales (INSHS - CNRS) | Sciences humaines et sociales, droit, sociologie |
| **LIEPP** | `218465` | Laboratoire interdisciplinaire d'évaluation des politiques publiques (Sciences Po) | Évaluation interdisciplinaire des politiques publiques |
| **PSE** | `301309` | Paris School of Economics - École d'économie de Paris | Modélisation économique, économie publique et climat |
| **CEPII** | `110493` | Centre d'études prospectives et d'informations internationales | Économie internationale et commerce |
| **CNRS** | `441569` | Centre National de la Recherche Scientifique | Recherche fondamentale pluridisciplinaire |

*Cette liste est destinée à être complétée par les relecteurs humains au fil des analyses thématiques.*

### Commandes CLI HAL :
- `uv run csc hal search "taxe carbone" --proximity "taxe,carbone,3"` : recherche de proximité Solr.
- `uv run csc hal structure IPP --query "carbone"` : recherche ciblée sur une structure affiliée.
- `uv run csc hal get halshs-00557065` : affiche la fiche complète d'une publication HAL.
- `uv run csc hal structures` : affiche la liste des structures référencées.

---

## Licences

- **Code source** : [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE)
- **Données publiques et métadonnées** : [Licence Ouverte 2.0 (Etalab)](LICENSE-DATA)
- **Contenus éditoriaux et synthèses** : [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](LICENSE-CONTENT)
