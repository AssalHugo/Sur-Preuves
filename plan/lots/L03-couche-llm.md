# L03 — Couche LLM : Gemini uniquement, plafond de 10 $/mois, embeddings CPU

**Agent** : fort · **Phase** : POC · **Dépend de** : L02 · **Effort** : 1,5 j
**Fichiers autorisés** : `backend/src/csc/llm/`, `backend/src/csc/embed/`, `config/models.yaml`, `config/pricing.yaml`, `prompts/_exemple.md`, `backend/tests/llm/`, `backend/tests/embed/`

## Objectif
Créer un point d'entrée unique pour tous les appels LLM et d'embedding. Il utilise **la Batch API Gemini par défaut**, construit des prompts compatibles avec le **cache implicite**, archive chaque appel et **refuse toute dépense au-delà du plafond mensuel**.

## API cible
```python
result: T = await llm.run(
    prompt_id="extract_claims",  # prompts/extract_claims.md (en-tête YAML + gabarit Jinja2)
    variables={...},
    output_model=ClaimExtraction,  # sortie structurée native (JSON schema)
    role="extraction",  # -> config/models.yaml
    tier="paid",  # "paid" (défaut) | "free" (offre gratuite, données publiques uniquement)
)
job = await llm.submit_batch(
    prompt_id, items=[...], output_model=..., role=...
)  # mode normal en production
results = await llm.collect_batch(job.id)  # reprise possible
vectors = embed.passages(texts) / embed.query(text)  # local, CPU
```

## Fournisseurs
- **Implémentés maintenant** :
  - **Google** via `google-genai` (**pas** `google.generativeai`, obsolète) : temps réel et **Batch API**. Deux clés : `GEMINI_API_KEY` (projet payant) et `GEMINI_FREE_API_KEY` (projet sur l'offre gratuite, facultatif).
  - **`FakeProvider`** (réponses déterministes) pour les tests et le développement des autres lots.
- **Prévus plus tard, non implémentés** : Anthropic, Mistral, etc.
  - Le code expose une interface `Provider` (protocole Python : `generate`, `submit_batch`, `collect_batch`, `count_tokens`) et un registre de fournisseurs. Ajouter un fournisseur = écrire un adaptateur, sans toucher au reste.
  - Ne **pas** installer leurs SDK tant qu'ils ne servent pas.

## `config/models.yaml` (par défaut)
```yaml
extraction:       {provider: google, model: gemini-3.5-flash-lite, batch: true, thinking: low}
query_planning:   {provider: google, model: gemini-3.5-flash-lite, batch: true, thinking: low}
sms_grading:      {provider: google, model: gemini-3.5-flash-lite, batch: true, thinking: low}
synthesis:        {provider: google, model: gemini-4-argon,        batch: true, thinking: medium,
                   fallback: gemini-3.1-pro-preview}
synthesis_simple: {provider: google, model: gemini-3.5-flash-lite, batch: true, thinking: low}
verification:     {provider: google, model: gemini-3.5-flash-lite, batch: true, thinking: low}
stability:        {provider: google, model: gemini-4-argon,        batch: true, thinking: medium}
tone_lint:        {provider: google, model: gemini-3.5-flash-lite, batch: true}
embedding:        {provider: local,  model: intfloat/multilingual-e5-large}   # fastembed, CPU
verification_overrides:   # modèle de synthèse -> vérificateur
  gemini-3.5-flash-lite: gemini-3.1-flash-lite
policy:
  require_distinct_verification_model: true     # bloquant : verification.model != synthesis.model
  require_distinct_verification_provider: false # passer à true quand un 2e fournisseur sera ajouté
```
- **Règle bloquante** : refus de démarrer si `verification.model == synthesis.model` ou `== synthesis_simple.model` **pour les fiches qu'il vérifie**. Exemple concret : une fiche simple synthétisée par Gemini 3.5 Flash-Lite est vérifiée par `gemini-3.1-flash-lite`. Le routage se résout fiche par fiche (fonction `pick_verifier(synth_model)`, table `verification_overrides` dans `models.yaml`).
- Si `require_distinct_verification_provider` vaut `false` et que synthèse et vérification sont chez le même fournisseur, écrire `same_provider=true` dans chaque appel de vérification, avec un avertissement unique au démarrage.
- **Commande de test A/B** (POC) : `csc llm ab --role synthesis --models gemini-4-argon,gemini-3.1-pro-preview --sample eval/synthesis/ab20.jsonl` génère les deux versions de chaque fiche pour une notation à l'aveugle (L11).
- Changer de modèle ne demande **aucune** modification de code.

## Plafond budgétaire strict
1. **Registre des dépenses** : chaque `LlmCall` stocke `cost_usd`, calculé depuis `config/pricing.yaml` avec le tarif batch et la date, et les tokens réels, réflexion comprise. Les changements de prix datés doivent être gérés, en particulier **Gemini 4 Argon ×2 au 1/12/2026** et **Gemini 3.8 Flash ×2 au 1/1/2027**.
2. **Plafond mensuel interne `LLM_MONTHLY_CAP_USD` (défaut : 9 $)**, mois civil. Il peut être relevé ponctuellement par variable d'environnement, par exemple en mars, quand les crédits existants couvrent le dépassement. Chaque relèvement est journalisé.
3. **Contrôle *avant* envoi** : estimer le coût du job (entrée comptée avec `count_tokens`, sortie estimée = `max_output_tokens`). **Refuser** (`BudgetExceeded`) si `dépensé_ce_mois + estimation > plafond`. Un batch peut être **découpé** automatiquement pour tenir dans l'enveloppe restante, le reste étant reporté.
4. **Rapprochement après exécution** : le coût réel remplace l'estimation, avec alerte si l'écart dépasse 20 %.
5. Le **plafond de projet AI Studio** (*Project Spend Cap*) est réglé à 10 $/mois par l'humain, comme filet de sécurité, car Google peut facturer quelques minutes en retard. Documenter la procédure dans le README.
6. CLI :
   - `csc llm budget` : dépensé, reste, projection, détail par rôle et modèle ;
   - `csc llm cost --since …` ;
   - `csc llm estimate <job>` : simulation sans appel.

## Règles d'économie
- **Batch obligatoire** pour `tier="paid"`. Le temps réel n'est permis qu'avec `--debug`, et compte dans le plafond.
- **Cache implicite** : gabarits avec un **préfixe stable et long** (instructions, méthode, schéma) **avant** les variables. Un test vérifie que les variables n'apparaissent jamais dans les N premiers tokens. Gemini 4 Argon ne supporte **que** le cache implicite.
- **Pas de cache explicite** (`cachedContents`). Sur les modèles qui le proposent, le stockage est facturé à l'heure.
- **`max_output_tokens`** et **niveau de réflexion** fixés par rôle ; jamais illimités.
- **Cache local** : clé = (prompt_sha, modèle, paramètres, variables). Un hit renvoie la sortie archivée gratuitement, ce qui garantit aussi la reproductibilité.

## Garde-fou de l'offre gratuite
`tier="free"` n'accepte que des entrées marquées `public=True` (programmes, abstracts, rapports publics). Sur l'offre gratuite, Google peut utiliser les données et des humains peuvent les relire. Tout appel contenant des commentaires de relecteurs, des données personnelles ou des fiches non publiées est **rejeté** avant envoi (test). Gemini 4 Argon n'a pas d'offre gratuite.

## Embeddings CPU (`csc.embed`)
- **`fastembed`** (ONNX Runtime, CPU). Par défaut **`intfloat/multilingual-e5-large`** (1024 dim.) ; pour le développement, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dim.). Ne **pas** utiliser `bge-small-en-v1.5`, anglais uniquement.
- Préfixes e5 obligatoires : `"query: "` pour les requêtes, `"passage: "` pour les documents.
- `parallel=0` (tous les cœurs), lots de 64, reprise après interruption, poids en cache dans `var/models/`.
- Dimension vérifiée au démarrage par rapport à la colonne `vector(n)` (L02).

## Sécurité
Réglages de sécurité par défaut, sans `BLOCK_LOW_AND_ABOVE`. Le contenu tiers est encadré par des balises et traité comme une donnée, jamais comme une instruction. Retries avec backoff ; timeouts.

## Critères d'acceptation
- Tests avec `FakeProvider` : sortie structurée valide ; sortie invalide → 1 retry puis erreur ; cache hit ; **dépassement de plafond refusé avant envoi** ; batch découpé ; changement de prix daté (Argon au 1/12/2026) ; appel `free` avec données non publiques rejeté ; **configuration où synthèse et vérification utilisent le même modèle refusée**.
- Test : l'embedding de 1 000 passages avec MiniLM tourne sur CPU ; la dimension est cohérente avec la base.
- Tests réels marqués `@pytest.mark.live`, exclus de la CI. L'un d'eux **vérifie l'accès du compte à `gemini-4-argon`** et indique clairement s'il faut basculer sur le repli.
- `csc llm budget` cohérent après un batch réel de 10 éléments (coût inférieur à 0,01 $ sur Flash-Lite).
