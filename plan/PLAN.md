# Plan d'implémentation — Comparateur « Programmes présidentiels 2027 × état de la science »

> Document de pilotage. Établi le 27 octobre 2026 à partir du rapport Gemini « Comparateur Politique et Science » et de vérifications en ligne.
> **Révision 3 (27/10/2026)** : **POC 100 % local d'abord**, **Gemini uniquement** (Gemini 4 Argon pour la synthèse), plafond de **10 $/mois**, hébergement payant du back-office repoussé à plus tard.
> Les lots détaillés sont dans [`lots/`](lots/). Chaque lot peut être confié tel quel à un agent IA de code.

---

## 0. Contraintes et phasage

| Contrainte | Valeur actuelle |
|---|---|
| LLM | **Gemini uniquement** pour l'instant (crédits existants + **10 $/mois**). Les autres fournisseurs viendront plus tard ; l'architecture les prévoit sans les implémenter |
| Matériel | PC avec **CPU puissant, sans GPU**. Tous les traitements tournent dessus |
| Back-office | **En local** pour le POC. Hébergement payant prévu plus tard, avant d'ouvrir la relecture aux chercheurs |
| Rigueur | Inchangée : relecture humaine obligatoire, règle de sélection symétrique, traçabilité complète |

| Phase | Objectif | Où ça tourne | Lots |
|---|---|---|---|
| **1. POC local** (nov. 2026) | Chaîne complète de bout en bout sur un petit corpus : ingestion → extraction → preuves → synthèse → vérification → relecture → bundle → site, **tout sur `localhost`** | PC local | L01 → L12, L14 et L15 en version locale |
| **2. Production** (déc. 2026 → mars 2027) | Passage à l'échelle (≈ 330 fiches), bilan de législature, recrutement et relecture par des chercheurs | PC local pour les traitements ; **back-office sur un hébergement payant** (à choisir) | L13, L14 hébergé, L17 |
| **3. Publication** (févr. → mai 2027) | Site public, formulaire de rectification, gel électoral | Cloudflare Pages (0 €) + back-office hébergé | L15, L16 |

## 1. Ce qu'il faut retenir du rapport Gemini

- **Ne jamais noter un candidat.** On évalue seulement (a) les **constats factuels** et (b) la **plausibilité des mécanismes causaux**, à partir de la littérature.
- **Séparer le normatif du positif.** Les objectifs politiques sont écartés de l'évaluation.
- **Grilles de qualité des preuves** : l'échelle de Maryland (SMS 1 à 5) et la méthode Science Feedback.
- **Trois piliers de données** : programmes (dont professions de foi FALC), votes et amendements, littérature et rapports institutionnels.
- **L'IA ne parle jamais directement au public.** Tout est pré-calculé, sourcé, relu, puis publié en pages statiques.
- **Zéro profilage** : pas de compte visiteur, pas de cookie, pas de « boussole électorale ».
- **Transparence** : code et prompts publics, traçabilité par fiche, droit de réponse, historique des corrections.

## 2. Corrections et mises à jour (vérifiées en ligne le 27/10/2026)

| # | Ce que dit le rapport | Ce qui est vrai aujourd'hui | Conséquence sur le plan |
|---|---|---|---|
| 1 | Scrutin « avril-mai 2027 » | **18 avril et 2 mai 2027** | Calendrier §7. |
| 2 | Restrictions L.52-1 « dès le 1er novembre 2026 » | Elles courent **depuis le 1er octobre 2026** | Aucune publicité payante. |
| 3 | Gel « vendredi 23h59 » | L'outre-mer et les Amériques votent **le samedi** | Gel dès le **jeudi 23h59**, à valider juridiquement (L16). |
| 4 | NosDéputés.fr | Plus maintenu après la XVIe législature | **NosParlementaires** + open data de l'AN (L07). |
| 5 | OpenAlex « sans clé » | **Clé gratuite**, budget gratuit de **1 $/jour** | Cache et usage dans l'enveloppe gratuite (L04). |
| 6 | MCP HAL dans le pipeline | **Expérimental**, peut halluciner | **API REST Solr** de HAL (L05). |
| 7 | SDK `google.generativeai` | Remplacé par **`google-genai`** | L03. |
| 8 | `temperature=0` reproductible | C'est faux | **Archivage** de chaque sortie (L03). |
| 9 | Tout le GIEC, le HCC… en *context caching* | Corpus trop volumineux ; Gemini 4 Argon **ne propose que le cache implicite** ; sur d'autres modèles, le stockage du cache explicite est facturé à l'heure | **RAG local** (pgvector + embeddings CPU), dossiers ≤ 25k tokens, cache implicite uniquement (L08, L10). |
| 10 | « Chaque phrase porte un DOI » | Un LLM peut inventer des DOI | Citations limitées aux identifiants `E1…En` ; **contrôles déterministes** (DOI, page, nombres) ; vérification par un **second modèle** (L12). |
| 11 | `BLOCK_LOW_AND_ABOVE` | Blocages à tort sur des textes politiques | Réglages par défaut. |
| 12 | Hypothes.is pour la relecture | Pas de circuit de validation | **Back-office dédié** (L14). |
| 13 | AI Act, Art. 50 | En vigueur depuis le 2 août 2026 ; haut risque (Annexe III) reporté au **2 décembre 2027** | Mention IA et journal de relecture. |

## 3. Architecture

### 3.1 Phase POC : tout en local

```
┌──────────────────────────── PC LOCAL (CPU, sans GPU) ─────────────────────────────┐
│                                                                                   │
│  Connecteurs (CLI csc)          docker compose : PostgreSQL 16 + pgvector          │
│  L04 OpenAlex ─┐                (127.0.0.1:5432, volume local)                     │
│  L05 HAL ──────┤──────────────▶        ▲                                           │
│  L07 Parlement ┤                       │                                           │
│  L08 Docling + fastembed (CPU) ────────┤                                           │
│                                        ▼                                           │
│  Pipeline : L09 extraction ─▶ L10 preuves ─▶ L11 synthèse ─▶ L12 vérification      │
│                 └──────────── L03 couche LLM (plafond 10 $/mois, batch) ───────────┼──▶ API Gemini
│                                        │                                           │
│  L14 back-office (FastAPI) ── http://127.0.0.1:8000 (relecture par toi)            │
│                                        │ csc publish bundle                        │
│  L15 site Astro ── npm run build && npm run preview ── http://127.0.0.1:4321       │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Phases production et publication (plus tard)
- **Back-office** : déployé sur un **hébergement payant** (VPS UE ou PaaS, à choisir au moment de l'ouverture aux chercheurs). Il est livré dès le POC sous forme de **conteneur Docker** pour que ce passage ne demande aucune réécriture. Ordre de grandeur : un petit VPS UE comme Hetzner CX23 coûte environ 5,49 €/mois HT (prix de juin 2026), à revérifier le moment venu.
- **Site public** : **Cloudflare Pages** (0 €), déploiement par GitHub Actions avec contrôle du gel (L16).
- **Formulaire de rectification** : Pages Function + D1 + Turnstile (0 €).
- **Traitements lourds** : restent sur le PC local ; seul le bundle publié et la base de relecture sont synchronisés.

Principes : (1) le site public ne dépend jamais du PC ; (2) le contrat de données (L02) est la colonne vertébrale ; (3) chaque appel LLM est archivé.

## 4. Stack technique

| Couche | Choix | Coût | Phase |
|---|---|---|---|
| Exécution | **PC local**, `docker compose` (Postgres + pgvector, back-office) et CLI `csc` (Python 3.12, `uv`) | 0 € | POC |
| Base | **PostgreSQL 16 + pgvector** en local ; `pg_dump` quotidien sur un disque externe | 0 € | POC |
| Parsing PDF | **Docling sur CPU** ; OCR Tesseract seulement pour les PDF scannés | 0 € | POC |
| Embeddings | **`fastembed` (ONNX, CPU)** avec **`intfloat/multilingual-e5-large`** ; MiniLM multilingue pour le développement | 0 € | POC |
| LLM | **API Gemini uniquement** (`google-genai`), batch | ≈ 43 $ au total | POC → production |
| Back-office | FastAPI + Jinja2 + HTMX, **conteneur Docker**, `127.0.0.1` | 0 € puis hébergement payant | POC local → hébergé |
| Site | **Astro 5 statique + Tailwind + Pagefind**, `npm run preview` en local | 0 € | POC |
| Hébergement du site | **Cloudflare Pages** (repli : GitHub Pages, limite souple de 100 Go/mois) | 0 € | Publication |
| Sauvegardes hors site | R2 (offre gratuite de 10 Go), chiffrées avec age | 0 € | Production |
| CI | GitHub Actions (dépôt public) | 0 € | POC |
| Domaine | Facultatif | ~10 €/an | Publication |

## 5. Stratégie LLM : Gemini uniquement (prix au 27/10/2026, en $ par million de tokens)

### 5.1 Gemini 4 Argon ou Gemini 3.1 Pro pour la synthèse ?

| | Gemini 4 Argon | Gemini 3.1 Pro (preview) |
|---|---|---|
| Sortie | 30 septembre 2026 | 19 février 2026 |
| Benchmarks (agrégateurs) | **Devant sur la plupart** (raisonnement, agentique, connaissances) | Une source le donne **devant en exactitude factuelle** |
| Batch jusqu'au 30/11/2026 | **1 / 5** | 1 / 6 |
| Batch **dès le 1/12/2026** | **2 / 10** | 1 / 6 |
| Cache | **Implicite uniquement** (0,10, puis 0,20) | Implicite et explicite |
| Offre gratuite | Non | Non |
| Coût d'une fiche causale (25k + 6k) | 0,055 $ en nov. → **0,11 $** ensuite | 0,061 $ |

**Décision** : **Gemini 4 Argon par défaut** pour la synthèse. C'est le modèle le plus récent, et le POC tombe en novembre, pendant la période à moitié prix. Mais l'**exactitude factuelle** est le critère n°1 du projet. Le POC inclut donc un **test A/B** : mêmes 20 fiches générées par les deux modèles, notées en aveugle par toi ou un relecteur, avec le taux de citations validées par L12. Coût : environ 1 à 2 $. On garde Argon sauf s'il est nettement moins exact. Le choix tient en une ligne de `config/models.yaml`. Vérifier aussi que ton compte a bien accès à Argon : l'accès est encore en cours d'élargissement selon certaines sources.

### 5.2 Modèles par rôle

| Rôle (lot) | Modèle | Batch (entrée / sortie) |
|---|---|---|
| Extraction et classification (L09) | **Gemini 3.5 Flash-Lite** | 0,15 / 1,25 |
| Requêtes et qualification SMS (L10) | **Gemini 3.5 Flash-Lite** (après pré-tri par heuristiques) | 0,15 / 1,25 |
| Synthèse des fiches **causales** (L11) | **Gemini 4 Argon** | 1 / 5 → **2 / 10 au 1/12** |
| Synthèse des fiches **factuelles simples** (L11) | **Gemini 3.5 Flash-Lite** | 0,15 / 1,25 |
| **Vérification des citations** (L12) | **Gemini 3.5 Flash-Lite** pour les fiches Argon ; **Gemini 3.1 Flash-Lite** pour les fiches rédigées par 3.5 Flash-Lite (toujours un modèle **différent** du rédacteur) | 0,15 / 1,25 et 0,125 / 0,75 |
| Test de stabilité (L12, 10 %) | Gemini 4 Argon | 2 / 10 |
| Embeddings (L08) | **fastembed, local** | 0 $ |

### 5.3 Vérification sans second fournisseur : ce que ça change
Le plan précédent confiait la vérification à un autre fournisseur, pour que les erreurs ne soient pas corrélées. Avec Gemini seul :
- la vérification utilise un **modèle différent** de celui de la synthèse (règle **bloquante** dans L03) ;
- les **contrôles déterministes**, sans LLM, restent la première ligne : résolution des DOI, extrait présent à la page citée, nombres retrouvés dans les sources, lexique évaluatif ;
- la **relecture humaine** reste obligatoire ;
- chaque `VerificationReport` enregistre `same_provider=true`, et la méthodologie publique le mentionne ;
- **recommandé avant l'ouverture publique** : ajouter un vérificateur d'un autre fournisseur. La couche L03 a l'interface prête ; il suffit d'écrire un adaptateur. Le coût serait de quelques dollars.

### 5.4 Règles d'économie (appliquées par L03)
1. **Batch API systématique** (−50 %).
2. **Cache implicite seulement** : préfixe stable en tête de prompt. Argon ne supporte pas le cache explicite.
3. **Offre gratuite de Gemini** (Flash-Lite, 3.8 Flash) pour la mise au point des prompts, **uniquement sur données publiques**. Google peut y réutiliser les entrées, et des humains peuvent les relire.
4. **Double plafond** : *Project Spend Cap* AI Studio réglé à **10 $/mois**, et plafond interne L03 à **9 $/mois**.
5. **Dossiers ≤ 25k tokens**, réflexion bornée, `max_output_tokens` fixé par rôle.

## 6. Budget

### 6.1 POC (novembre 2026, tarif Argon à moitié prix)

| Poste | Hypothèse | Coût |
|---|---|---|
| Extraction, preuves, vérification (Flash-Lite batch) | ~30 fiches | < 0,50 $ |
| Synthèse Argon (batch, nov.) | 30 fiches × 1,5 passe × 0,055 $ | ~2,5 $ |
| Test A/B Gemini 3.1 Pro | 20 fiches | ~1,2 $ |
| Mise au point des prompts | offre gratuite (données publiques) | 0 $ |
| **Total POC** | | **≈ 4 $** |

### 6.2 Production complète (≈ 330 fiches, à partir de décembre)

**Hypothèses** : 12 candidats × 20 à 25 propositions (règle symétrique, L00), plus 10 textes de législature (~30 fiches). Total ≈ 330 fiches, dont ~200 causales et ~130 simples ; relances ×1,3.

| Poste | Calcul | Coût |
|---|---|---|
| L09 extraction (Flash-Lite) | ~2,5M tokens en entrée, 0,5M en sortie | ~1,0 $ |
| L10 requêtes et SMS (Flash-Lite) | 430 × (12k + 3k) | ~2,4 $ |
| L11 synthèses causales (**Argon**, 2 / 10) | 260 × (25k + 6k) = 260 × 0,11 $ | **~28,6 $** |
| L11 synthèses simples (Flash-Lite) | 170 × (25k + 4k) | ~1,5 $ |
| L12 vérification (3.5 et 3.1 Flash-Lite) | 260 × 0,0055 $ + 170 × 0,004 $ | ~2,1 $ |
| L12 stabilité (Argon, 10 %) | 33 × 0,11 $ | ~3,6 $ |
| L12 analyse du ton (Flash-Lite) | | ~0,2 $ |
| Réserve pour la mise au point | | ~3,0 $ |
| **Total LLM (POC compris)** | | **≈ 43 $ (≈ 40 €)** |
| Infrastructure, phase POC | | **0 €** |
| *Hébergement du back-office (plus tard)* | *à décider ; ~5 à 10 €/mois pour un petit VPS UE* | *hors budget actuel* |

> **Levier si le budget serre** : n'utiliser Argon que pour les affirmations causales qui ont **au moins une preuve de niveau SMS ≥ 3** à synthétiser. Les mesures sans évaluation ex-post (`novel_no_ex_post`) passeraient sur Flash-Lite. Gain estimé : 20 à 30 % sur la ligne Argon. Cette règle reste **déterministe** et identique pour tous les candidats.

### 6.3 Lissage mensuel

| Mois | Activité | Gemini |
|---|---|---|
| nov. 2026 | **POC** (Argon à moitié prix) | ~4 $ |
| déc. 2026 | Jeux d'évaluation, stabilisation | ~3 $ |
| janv. 2027 | Bilan de législature (30 fiches) | ~5 $ |
| févr. 2027 | Premiers programmes, traités dès leur publication | ~9 $ |
| mars 2027 | Gros des programmes (liste officielle mi-mars) | **~15 $** : le plafond du projet sera relevé ce mois-là, le dépassement étant **payé sur les crédits existants**, ou le traitement étalé sur avril |
| avr. 2027 | Corrections, relances | ~6 $ |

## 7. Calendrier

| Période | Jalons | Lots |
|---|---|---|
| **28 oct → 30 nov 2026** | **POC local** (§8.1). Charte et règle de sélection en parallèle | L00 – L12, L14 (local), L15 (local) |
| **déc. 2026** | Résultats du POC, choix Argon / 3.1 Pro, jeux d'évaluation complets, recrutement des relecteurs, **choix de l'hébergement du back-office** | L09 – L12 durcis |
| **janv. 2027** | Back-office hébergé, bilan de législature, bêta privée | L13, L14 hébergé, L17 |
| **févr. → mi-mars** | Ouverture publique du site (Cloudflare Pages) ; programmes traités au fil de l'eau | L15, L16 |
| **~mi-mars** | Liste officielle ; **publication simultanée** pour tous les candidats | — |
| **jeu. 15/04 23h59 → dim. 18/04 20h00** | **Gel** (1er tour) | L16 |
| **jeu. 29/04 23h59 → dim. 02/05 20h00** | **Gel** (2nd tour) | L16 |

## 8. Lots

### 8.1 Définition du POC
- **Corpus** : propositions de la **présidentielle 2022**, environ 2 à 3 propositions pour chacun des 12 candidats de 2022, soit **~30 fiches**.
  - Le corpus est symétrique, et il ne touche pas à la campagne en cours.
  - Il peut être comparé à des évaluations publiées à l'époque (chiffrages IPP, OFCE, analyses du Shift Project), ce qui fournit une vérité de terrain.
- Plus **2 textes de la 17e législature** pour tester L07.
- **Critères de réussite** :
  1. Chaîne complète lancée par `make poc` sur le PC, sans GPU.
  2. 100 % des phrases citées pointent vers une preuve réelle, ce qui veut dire que les contrôles déterministes de L12 passent.
  3. Au moins 70 % des fiches jugées « publiables après corrections mineures » par toi ou un chercheur.
  4. Le site local affiche les fiches, avec onglets de traçabilité.
  5. Coût total ≤ 5 $, affiché par `csc llm budget`.
  6. Test A/B Argon / 3.1 Pro documenté.
- **Hors POC** : L06, L13 complet, L16, tunnel et hébergement, formulaire de rectification.

### 8.2 Graphe de dépendances

```
L00 (humain, en continu) ───────────────────────────────────────────────────────────▶
L01 ─▶ L02 ─▶ L03 ─┬─▶ L09 ─▶ L10 ─▶ L11 ─▶ L12 ─┬─▶ L14 ─▶ L15 ─▶ L16 (phase 3)
                   │                              └─▶ L13 (phase 2)
       L02 ─┬─▶ L04 ┤ (L10 a besoin de L04, L05, L08)
            ├─▶ L05 ┤
            ├─▶ L06 ┤ (optionnel, phase 2)
            ├─▶ L07 ┘
            └─▶ L08
L17 : phase 2
```

| Lot | Titre | Phase | Dépend de | Agent | Effort |
|---|---|---|---|---|---|
| [L00](lots/L00-gouvernance-juridique.md) | Gouvernance, neutralité, juridique | 1 → 3 | — | Humain (+ IA) | continu |
| [L01](lots/L01-socle-depot.md) | Socle local, Docker Compose, CLI, CI | **POC** | — | standard | 0,5 j |
| [L02](lots/L02-modele-donnees-contrats.md) | Modèle de données et contrats | **POC** | L01 | **fort** | 1,5 j |
| [L03](lots/L03-couche-llm.md) | Couche LLM Gemini, plafond, embeddings CPU | **POC** | L02 | **fort** | 1,5 j |
| [L04](lots/L04-connecteur-openalex.md) | Connecteur OpenAlex | **POC** | L02 | standard | 1 j |
| [L05](lots/L05-connecteur-hal.md) | Connecteur HAL | **POC** | L02 | standard | 0,5 j |
| [L06](lots/L06-connecteur-semantic-scholar.md) | Semantic Scholar (optionnel) | 2 | L02 | standard | 0,5 j |
| [L07](lots/L07-connecteur-parlementaire.md) | Votes et amendements | **POC** (partiel) | L02 | standard | 2 j |
| [L08](lots/L08-ingestion-documentaire-rag.md) | Ingestion Docling et RAG sur CPU | **POC** | L02, L03 | standard | 2 j |
| [L09](lots/L09-extraction-affirmations.md) | Extraction des affirmations | **POC** | L03 | **fort** | 2 j |
| [L10](lots/L10-recherche-preuves.md) | Recherche de preuves et SMS | **POC** | L04, L05, L08, L09 | **fort** | 2 j |
| [L11](lots/L11-synthese-fiche.md) | Synthèse de fiche (Argon) | **POC** | L10 | **fort** | 2 j |
| [L12](lots/L12-verification-croisee.md) | Vérification (contrôles déterministes + second modèle) | **POC** | L11 | **fort** | 2 j |
| [L13](lots/L13-bilan-legislature.md) | Bilan de législature (10 textes) | 2 | L07, L11 | standard | 1,5 j |
| [L14](lots/L14-backoffice-relecture.md) | Back-office (local, puis hébergé) | **POC** → 2 | L02 (+ L12) | standard | 3 j |
| [L15](lots/L15-site-public.md) | Site statique (local, puis Cloudflare Pages) | **POC** → 3 | L02 | standard | 3 j |
| [L16](lots/L16-ops-deploiement-gel.md) | Déploiement, sauvegardes, gel électoral | 3 | L14, L15 | standard | 1,5 j |
| [L17](lots/L17-transparence-conformite.md) | Méthodologie et conformité | 2 | L11 | standard + juriste | 1 j |

## 9. Mode d'emploi : faire réaliser un lot par une IA

1. **Une branche (ou un worktree) par lot**, une PR par lot, relue par un humain.
2. Donner à l'agent `AGENTS.md` (L01), ce `PLAN.md` et le fichier du lot.
3. Prompt de lancement :

```text
Tu travailles sur le dépôt « comparateur-science-2027 ».
Lis AGENTS.md, puis plan/PLAN.md (sections 0 à 5 et 8.1), puis plan/lots/<LOT>.md.
Réalise UNIQUEMENT ce lot, dans sa version « POC local » sauf indication contraire.
Ne modifie pas les fichiers hors de la section « Fichiers autorisés » ; si un changement
de contrat (L02) te paraît nécessaire, arrête-toi et décris-le dans PR_NOTES.md.
N'appelle aucune API LLM payante pendant le développement : FakeProvider ou offre
gratuite Gemini (données publiques uniquement).
Termine quand tous les « Critères d'acceptation » passent (`make check` vert).
Résume à la fin : ce qui est fait, ce qui ne l'est pas, les décisions prises.
```

4. **Définition de « terminé »** : `make check` vert, README à jour, aucune clé dans le code, aucune donnée de visiteur collectée, aucun service payant introduit sans décision humaine.
5. **Les changements de contrat (L02) passent par un humain.**

## 10. Risques principaux

| Risque | Impact | Parade |
|---|---|---|
| **Vérification par le même fournisseur** (Gemini) | Erreurs corrélées entre synthèse et vérification | Modèle différent obligatoire ; contrôles déterministes en premier ; relecture humaine ; `same_provider` affiché ; second fournisseur recommandé avant l'ouverture publique |
| **Hausse de prix d'Argon le 1er décembre** (×2) | Budget de production ≈ 43 $ | POC en novembre ; levier SMS ≥ 3 (§6.2) ; repli sur 3.1 Pro selon le test A/B |
| Accès à Argon pas encore ouvert sur ton compte | POC bloqué | Vérifier dès L03 ; repli sur `gemini-3.1-pro-preview` |
| Dépassement du plafond de 10 $ en mars | Pipeline arrêté | Double plafond ; traitement au fil de l'eau ; crédits existants |
| Offre gratuite de Gemini | Données réutilisables par Google | Réservée aux données publiques (règle L03) |
| PC unique, point de défaillance | Perte de données | `pg_dump` quotidien sur disque externe dès le POC, puis R2 en phase 2 |
| Relecteurs insuffisants | Fiches non publiables | Recrutement dès décembre ; périmètre de 20 à 25 propositions |
| Accusation de biais | Perte de crédibilité | Règle de sélection objective, ordre aléatoire, prompts publics, routage déterministe des modèles |
| Hallucination d'une source | Atteinte à la sincérité | Identifiants `E1…En`, contrôles déterministes, relecture |
| Pic de trafic | Site indisponible | Site statique sur Cloudflare Pages (phase 3) |

## Sources

- Tarifs Gemini API (dont Gemini 4 Argon, Flash-Lite, 3.1 Pro) — https://ai.google.dev/gemini-api/docs/pricing
- Comparaisons Argon / 3.1 Pro (agrégateurs) — https://llm-stats.com/models/compare/gemini-3.1-pro-preview-vs-gemini-4-argon ; https://emergent.sh/learn/gemini-4-argon-vs-gemini-3-1-pro ; https://benchlm.ai/compare/gemini-3-1-pro-vs-gemini-4-argon ; https://www.webreactiva.com/blog/gemini-4-argon
- Conditions Gemini API (offre gratuite) — https://ai.google.dev/gemini-api/terms
- Plafonds de dépense Gemini — https://blog.google/innovation-and-ai/technology/developers-tools/more-control-over-gemini-api-costs/ ; https://ai.google.dev/gemini-api/docs/billing
- fastembed, modèles supportés — https://qdrant.github.io/fastembed/examples/Supported_Models/
- Cloudflare Workers et Pages (offre gratuite) — https://developers.cloudflare.com/workers/platform/pricing/
- Limites GitHub Pages — https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- Hetzner (prix de juin 2026) — https://northflank.com/blog/hetzner-cloud-server-price-increases
- OpenAlex — https://help.openalex.org/how-to-use-the-api/rate-limits-and-authentication ; https://openalex.org/pricing
- MCP HAL — https://doc.hal.science/mcp/
- NosParlementaires — https://nosparlementaires.fr/donnees-ouvertes
- Dates de la présidentielle 2027 — https://www.service-public.gouv.fr/particuliers/actualites/A15053
- Digital Omnibus IA — https://www.addleshawgoddard.com/en/insights/insights-briefings/2026/technology/eu-ai-act-ai-omnibus-formally-adopted/
- AI Act Art. 50 — https://labs.cloudsecurityalliance.org/research/csa-research-note-eu-ai-act-article-50-transparency-20260729/
- L.52-1 — https://www.lesepl.fr/2019/08/quelles-sont-les-principales-restrictions-apportees-par-le-droit-electoral-dans-les-six-mois-precedant-les-elections/
