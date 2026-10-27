# Règles pour les agents d'assistance et d'ingénierie IA (AGENTS.md)

Ce document régit les interventions de tout agent IA sur le projet **Comparateur Science 2027** (`csc`).

---

## 1. Méthode de travail

- **Un lot = une PR** : toujours lire `plan/PLAN.md` et le document spécifique du lot (`plan/lots/Lxx-....md`) avant d'agir.
- **Fin de lot obligatoire** : la cible `make check` doit être verte à 100 %, sans avertissement ni contournement, accompagnée d'un fichier `PR_NOTES.md` résumant les modifications, tests exécutés et éventuelles limites.
- **Langue** :
  - Code, noms de variables/fonctions/classes, commits et tests : **en anglais**.
  - Documentation, prompts, contenus éditoriaux et messages d'interface : **en français**.

---

## 2. Architecture & Environnement technique

- **Local-first strict** :
  - Tous les traitements s'exécutent sur la machine locale (CPU uniquement, sans GPU ni dépendance CUDA).
  - Ne jamais introduire de service cloud payant.
  - Les dépendances doivent tourner sur CPU (roues CPU pour `fastembed`, `onnxruntime`, et `torch` si nécessaire pour Docling).
- **Stack Python** :
  - Python 3.12+ géré avec `uv`.
  - Pydantic v2 pour les modèles et la validation de données.
  - SQLAlchemy 2.0 (avec support `pgvector`).
  - Typage strict : passage obligatoire de `mypy --strict`.
  - Linting et formatage : `ruff check` et `ruff format`.
- **Traitements longs** :
  - Doivent impérativement être **reprenables** (idempotence, reprise sur erreur, journalisation).
  - Afficher une barre de progression dans la CLI (`rich.progress`).

---

## 3. Gestion des LLM

- **Fournisseur unique : Gemini** (`google-genai`), strictement encapsulé dans `csc.llm`.
- **Aucun autre SDK** (OpenAI, Anthropic, Mistral, etc.) ne doit être ajouté comme dépendance d'exécution pour le moment.
- **Interdiction formelle d'appeler l'API Gemini payante lors du développement et des tests** :
  - Utiliser `FakeProvider` / mocks pour les tests.
  - Pour les tests manuels ou prompts, utiliser l'offre gratuite Gemini avec des données publiques uniquement.
- Respecter le plafond budgétaire configuré (`LLM_MONTHLY_CAP_USD=9`).

---

## 4. Règles d'or et Interdictions

1. **Contrats immuables** : Interdiction de modifier `backend/src/csc/contracts/` sans validation explicite d'un humain.
2. **Secrets & Données** : Ne jamais committer de clés d'API, de secrets, ni le contenu du répertoire `var/` (`var/pdf/`, `var/cache/`, `var/models/`, `var/backups/`).
3. **Zéro appel réseau en test** : Les tests unitaires et d'intégration ne doivent jamais émettre de requête réseau réelle (utiliser `respx`, des mocks ou des fixtures/cassettes).
4. **Pas de contournement du LLM** : Tout appel LLM doit impérativement passer par l'abstraction `csc.llm` afin d'enregistrer la traçabilité (`LlmCall`).
5. **Respect de la vie privée & RGPD** : Zéro collecte de données visiteur, zéro cookie, zéro profileur.
