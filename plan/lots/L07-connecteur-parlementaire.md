# L07 — Connecteur parlementaire (votes, scrutins, amendements)

**Agent** : standard · **Dépend de** : L02 · **Effort** : 2 j
**Fichiers autorisés** : `backend/src/csc/connectors/parlement/`, `data/editorial/groupes_partis.yaml`, `backend/tests/connectors/parlement/`

## Contexte (vérifié le 27/10/2026)
- **NosDéputés.fr n'est plus maintenu au-delà de la XVIe législature** (annonce de Regards Citoyens). Il reste utile pour l'historique (`2017-2022.nosdeputes.fr`).
- **NosParlementaires** (`nosparlementaires.fr/donnees-ouvertes`) :
  - dumps CSV et JSON quotidiens (députés, sénateurs, scrutins, votes), avec manifeste SHA-256 ; licence Ouverte 2.0 ;
  - API v1 avec **clé gratuite** (`X-Api-Key`), **60 req/min** ; endpoints `/api/v1/scrutins`, `/api/v1/scrutins/{chamber}/{id}/votes`, `/api/v1/votes` (filtres par chambre, thème, groupe, période), `/api/v1/deputies`, `/api/v1/themes` ;
  - votes des députés de la XIVe à la XVIIe législature, votes des sénateurs depuis 2006 ;
  - **ne couvre pas les amendements**.
- **Open data officiel de l'Assemblée** (`data.assemblee-nationale.fr`) : amendements, dossiers législatifs et scrutins en XML ou JSON (identifiants du type `AMANR5L17…`, `VTANR5L17V…`). C'est la source de référence pour les amendements.
- Sénat : `data.senat.fr`.

## Tâches
1. **Votes et scrutins** : importer les dumps NosParlementaires (préférés à l'API pour le volume), puis faire une mise à jour incrémentale quotidienne. Vérifier le SHA-256 du manifeste.
2. **Amendements (AN, 17e législature)** : télécharger le dump officiel et parser vers `Amendment {id, dossier, article, auteurs, groupe, exposé des motifs, dispositif, sort, scrutin_id?}`.
3. **Dossiers législatifs** : lier dossier ↔ amendements ↔ scrutins.
4. **Table éditoriale `groupes_partis.yaml`** : correspondance groupe parlementaire ↔ parti ↔ candidat, **remplie et validée par un humain**. Le connecteur ne fait que la lire.
5. Fonction d'agrégation : `group_positions(dossier_id) -> {group: {pour, contre, abstention, non_votant}}`, par scrutin, en distinguant **vote solennel** et **votes d'articles et d'amendements**. Ce point est souligné dans le rapport Gemini.

## Exigences
- Conserver les identifiants officiels (`VTANR5L17V…`) : ils sont cités dans les fiches.
- Attribution « Données : Assemblée nationale, Sénat, NosParlementaires (Licence Ouverte 2.0) » stockée avec chaque enregistrement.

## Critères d'acceptation
- Import complet de la 17e législature en moins de 15 minutes en local ; idempotent (relancer ne duplique rien).
- Tests sur un échantillon de fichiers XML/JSON committés (5 amendements, 3 scrutins).
- `csc parlement dossier <id>` affiche les positions des groupes, solennel et amendements séparés.
