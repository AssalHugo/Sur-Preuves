# Notes de Révision — Lot L03 : Couche LLM & Embeddings CPU

## 1. Contexte et Objectifs
Le lot L03 implémente la couche d'accès LLM et d'embeddings pour le **Comparateur Science 2027** (`csc`), conformément aux contraintes de `plan/lots/L03-couche-llm.md` et de `AGENTS.md` :
- **Point d'entrée unifié et immuable** pour toutes les inférences de texte (`csc.llm`) et la vectorisation (`csc.embed`).
- **Fournisseur unique Gemini** (`google-genai`), strictement encapsulé, sans dépendance cloud payante additionnelle.
- **Batch API obligatoire par défaut** pour le palier payant (-50 % sur les tarifs).
- **Double plafond mensuel** : plafond logiciel strict à 9,00 $/mois (`LLM_MONTHLY_CAP_USD`) avec rejet **avant** tout appel (`BudgetExceededError`), et filet de sécurité à 10,00 $/mois documenté pour Google AI Studio (*Project Spend Cap*).
- **Architecture de prompts compatible avec le cache implicite** de Gemini (préfixe méthodologique stable avant toute interpolation de variable).
- **Vérification croisée découplée** : interdiction bloquante au démarrage de faire vérifier une synthèse par le même modèle que son rédacteur (table `verification_overrides`).
- **Garde-fou strict de confidentialité sur l'offre gratuite** : rejet automatique de Gemini 4 Argon, des données privées (e-mails, téléphones), des fiches non publiées et des avis de relecteurs, avec obligation d'un drapeau explicite `public=True`.
- **Embeddings 100 % CPU locaux** via `fastembed` (ONNX Runtime, sans CUDA ni GPU), préfixes e5 obligatoires (`query: `, `passage: `), traitement reprenable par point de contrôle et vérification de la dimension (1024 pour la base, 384 pour le dev).

Tous les critères d'acceptation du lot L03 sont vérifiés et atteints à 100 %, sans avertissement ni contournement.

---

## 2. Modifications Réalisées

### A. Grille Tarifaire et Tarifs Datés (`config/pricing.yaml`, `csc.llm.pricing`)
- Fichier déclaratif `config/pricing.yaml` :
  - Tarifs en USD par million de tokens pour `gemini-4-argon`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`, `gemini-3.8-flash`.
  - Gestion native des **changements tarifaires datés** via la directive `schedule` :
    - **Gemini 4 Argon** : tarif batch à 1,00 $ entrée / 5,00 $ sortie jusqu'au 30/11/2026, puis **doublement au 01/12/2026** (2,00 $ entrée / 10,00 $ sortie).
    - **Gemini 3.8 Flash** : tarif batch à 0,15 $ / 1,25 $ en 2026, puis **doublement au 01/01/2027** (0,30 $ / 2,50 $).
  - Gestion de la gratuité stricte pour le palier `free` (`cost_usd = 0.0`).
  - Prise en compte des tokens de réflexion (`thinking_tokens`) facturés au tarif de sortie, et des tokens de cache (`cached_tokens`) au tarif réduit de cache implicite.
  - Estimation préalable de coût (`estimate_call_cost`) avant exécution.

### B. Routage des Modèles et Politique de Non-Corrélation (`config/models.yaml`, `csc.llm.models_config`)
- Fichier `config/models.yaml` définissant les rôles opérationnels du projet :
  - `extraction`, `query_planning`, `sms_grading`, `synthesis_simple`, `verification`, `tone_lint` (`gemini-3.5-flash-lite`).
  - `synthesis`, `stability` (`gemini-4-argon`, avec repli documenté `gemini-3.1-pro-preview`).
- Fonction de routage dynamique `pick_verifier(synth_model)` et validation au démarrage (`validate_configuration`) :
  - **Règle bloquante** : refus de démarrer si le modèle de vérification est identique au modèle de synthèse.
  - Table `verification_overrides` : pour les fiches simples générées par `gemini-3.5-flash-lite`, la vérification est automatiquement basculée sur `gemini-3.1-flash-lite`.
  - Enregistrement systématique de `same_provider=true` dans les métadonnées de vérification et émission d'un avertissement unique au démarrage.

### C. Abstraction des Fournisseurs (`csc.llm.providers`)
- Protocole Python strict `Provider` (`generate`, `submit_batch`, `collect_batch`, `count_tokens`) et registre `ProviderRegistry`.
- `GoogleProvider` : implémentation complète sur le SDK officiel `google-genai` (asynchrone avec `client.aio`), support de la Batch API (`client.aio.batches`), comptage de tokens (`client.aio.models.count_tokens`) et retries avec backoff exponentiel.
- `FakeProvider` : implémentation déterministe pour les tests et développements hors ligne, avec file de réponses programmables (pour tester les relances en cas de sortie invalide).

### D. Plafond Budgétaire & Sécurité Financière (`csc.llm.budget`)
- Classe `BudgetManager` :
  - Plafond mensuel interne configurable via `LLM_MONTHLY_CAP_USD` (défaut : 9,00 $ USD).
  - Contrôle **avant émission** : calcul de `spent_this_month + estimated_cost`. Levée de l'exception `BudgetExceededError` en cas de dépassement.
  - Découpage automatique des lots (`split_batch_to_fit`) : calcul du nombre exact d'éléments admissibles dans l'enveloppe restante, report du reste.
  - Rapprochement post-exécution (`reconcile`) avec alerte journalisée si l'écart dépasse 20 %.
  - Journalisation de tout relèvement ponctuel du plafond mensuel.
  - Double persistance des dépenses : table `llm_calls` en base de données et registre local JSON (`var/cache/llm/budget_ledger.json`).

### E. Cache Local & Prompts (`csc.llm.cache`, `csc.llm.prompts`, `prompts/_exemple.md`)
- `LocalLlmCache` : hachage déterministe SHA-256 basé sur `(prompt_sha, model, params, variables)`. Un cache hit renvoie immédiatement la sortie archivée à un coût de 0,00 $ USD sans appel réseau.
- `PromptManager` : chargement des gabarits dans `prompts/`, extraction de l'en-tête YAML et corps Jinja2, calcul de l'empreinte `prompt_sha`.
- Contrôle du **cache implicite** : vérification que les instructions et la méthodologie forment un préfixe stable avant toute variable dynamique (`min_prefix_tokens`).

### F. Garde-Fou de l'Offre Gratuite (`csc.llm.guardrails`)
- Validation stricte des données soumises au palier `free` (`validate_free_tier`) :
  - Interdiction de `gemini-4-argon` (pas d'offre gratuite).
  - Obligation d'un paramètre explicite `public=True` ou `is_public=True`.
  - Rejet automatique en cas de détection d'avis de relecteurs, de brouillons non publiés, d'adresses e-mails ou de numéros de téléphone.

### G. Client Unifié `csc.llm.client` (`llm`)
- `await llm.run(...)` : appel structuré direct (réservé au développement avec `debug=True` sur le palier payant). En cas de JSON invalide, réalise exactement **1 relance** avant de lever `StructuredOutputError`.
- `await llm.submit_batch(...)` : soumission par lot (mode standard en production).
- `await llm.collect_batch(...)` : récupération et traçabilité immuable (`LlmCallModel`).

### H. Embeddings CPU (`csc.embed.embedder`)
- `CpuEmbedder` : exécution locale ONNX Runtime via `fastembed`.
- Modèle par défaut : `intfloat/multilingual-e5-large` (1024 dim.), modèle dev : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dim.).
- Interdiction formelle de `bge-small-en-v1.5` (anglophone).
- Préfixage obligatoire : `"query: "` pour les requêtes, `"passage: "` pour les documents.
- Configuration multithread CPU (`parallel=0` pour tous les cœurs, batchs de 64).
- Traitement reprenable après interruption (`embed_passages_resumable`) avec sauvegarde par point de contrôle.
- Vérification au démarrage de la cohérence dimensionnelle (`check_dimension`) avec la colonne `vector(1024)`.

### I. Commandes CLI Typer (`backend/src/csc/cli.py`)
- `csc llm budget` : affichage du plafond, dépensé, reste, projection et ventilations sous forme de tableaux Rich.
- `csc llm cost --since YYYY-MM-DD` : tableau d'audit des appels et dépenses depuis une date.
- `csc llm estimate <prompt_id> --items-count N` : simulation d'estimation des tokens et coûts temps réel vs batch sans appel réseau.
- `csc llm ab --role synthesis --models ... --sample ...` : préparation et exécution du banc d'essai comparatif aveugle.

### J. Données et Documentation
- `prompts/_exemple.md` : gabarit de référence respectant le préfixe long et stable.
- `eval/synthesis/ab20.jsonl` : jeu de données de 20 propositions témoins représentatives couvrant 15 thèmes pour le test A/B.
- `README.md` : ajout de la documentation de la couche LLM, des commandes CLI associées et de la procédure pour configurer le *Project Spend Cap* de Google AI Studio à 10 $/mois.

---

## 3. Résultats des Tests et Contrôles Qualité

La cible **`make check` est verte à 100 %** :
1. **Formatage Python (`ruff format`)** : 100 % conforme (78 fichiers vérifiés).
2. **Linting Python (`ruff check`)** : 0 erreur, 0 avertissement.
3. **Typage statique strict (`mypy --strict`)** : **0 erreur sur 50 fichiers source** (y compris tests et nouveau code).
4. **Tests Python (`pytest`)** :
   - **97 tests passés avec succès** en 1,36 s (sans aucun appel réseau réel en test unitaire).
   - **31 nouveaux tests** couvrant exhaustivement :
     - Les tarifs datés (Argon au 1/12/2026 x2, Flash au 1/1/2027 x2, tokens de cache, tokens de réflexion, gratuité du palier free).
     - La politique de modèles distincts synthèse/vérification et les tables de dérogation.
     - Les garde-fous de confidentialité de l'offre gratuite (Argon, public=True, avis de relecteurs, données personnelles).
     - Le chargement de gabarits Jinja2 et l'interdiction de variables en tête de prompt.
     - Le respect strict du plafond budgétaire avant appel, le découpage automatique de lots et les alertes de réconciliation.
     - L'orchestrateur `llm.run` avec `FakeProvider` (sortie valide, 1 retry sur erreur, cache hit à coût 0, interdiction du temps réel payant sans debug, batching, collecte via `job.id` ou objet `BatchJob`).
     - La configuration de réflexion (`thinking`) sur `GoogleProvider` en mode unitaire et batch.
     - L'embedding CPU de 1 000 passages avec MiniLM, les préfixes e5 obligatoires, la vérification dimensionnelle et la reprise sur incident avec sauvegarde atomique.
   - **2 tests réels Gemini (`@pytest.mark.live`)** isolés de la CI (exécutables manuellement avec `pytest -m live`).
5. **Site Astro** :
   - `astro check` : 0 erreur, 0 avertissement.
   - `astro build` : compilation statique 100 % réussie.

---

## 4. Limites et Prochaines Étapes
- Le SDK Gemini (`google-genai`) est configuré pour le palier gratuit et le palier payant. Pour exécuter des requêtes réelles hors tests unitaires, renseigner `GEMINI_API_KEY` dans `.env`.
- Le lot suivant (L04 — Connecteur OpenAlex) pourra s'appuyer directement sur `csc.llm` et les contrats de données de L02.
