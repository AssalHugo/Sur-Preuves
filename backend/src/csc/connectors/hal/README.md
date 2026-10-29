# Connecteur HAL (Archive Ouverte Nationale — CCSD / CNRS)

Le connecteur HAL permet d'interroger en temps réel le corpus scientifique français déposé sur l'archive ouverte nationale [HAL](https://hal.science) (articles de revues, rapports institutionnels, thèses de doctorat, chapitres d'ouvrages).

---

## 1. Architecture et Principes

- **API Solr directe** : point d'accès `https://api.archives-ouvertes.fr/search/?wt=json`, libre d'accès et sans authentification requise.
- **Serveur MCP (`https://api.archives-ouvertes.fr/mcp`)** : ce serveur est explicitement documenté comme **expérimental** par le CCSD. Ses réponses peuvent être incomplètes ou comporter des hallucinations, et il ne renvoie que des métadonnées partielles. **Il est strictement exclu du pipeline de production automatique**, mais peut servir à l'exploration manuelle ou interactive par un humain.
- **Cache local persistant (TTL 30 jours)** : les requêtes sont mises en cache sur disque dans `var/cache/hal/` avec un hachage SHA-256 déterministe des URLs et des paramètres normalisés.
- **Traçabilité publique (`EvidenceQuery`)** : chaque requête génère un enregistrement horodaté vérifiable (paramètres, URL, nombre de résultats).
- **Déduplication** : normalisation systématique des DOI en minuscules pour fusion ultérieure avec OpenAlex (Lot L10).

---

## 2. Fonctions Python exposées

```python
from csc.connectors.hal import search, search_by_structure, get

# 1. Recherche avec proximité Solr et filtres de types
works = search(
    query="taxe carbone",
    proximity=("taxe", "carbone", 3),  # '"taxe carbone"~3'
    doc_types=("ART", "REPORT", "THESE", "COUV"),
    since_year=2005,
    rows=50,
)

# 2. Recherche filtrée par structures de recherche (ex: IPP et OFCE)
works_ipp = search_by_structure(
    struct_ids=[266522, 250936],
    query="transition écologique",
    since_year=2015,
)

# 3. Récupération unitaire par identifiant HAL
work = get("halshs-00557065")
```

---

## 3. Référentiel des structures de recherche AuréHAL (`structId_i`)

Le tableau suivant répertorie les identifiants numériques de structures utiles (`structId_i`) au sein du référentiel AuréHAL pour cibler les expertises économiques, environnementales et de politiques publiques :

| Acronyme | `structId_i` | Intitulé officiel complet | Domaine d'expertise |
|---|---|---|---|
| **IPP** | `266522` | Institut des Politiques Publiques | Évaluation quantitative et micro-économique des politiques publiques (PSE/GENES) |
| **OFCE** | `250936` | Observatoire français des conjonctures économiques (Sciences Po) | Macroéconomie, prévisions, fiscalité carbone, politiques environnementales et européennes |
| **INRAE** | `577435` | Institut National de Recherche pour l’Agriculture, l’Alimentation et l’Environnement | Agriculture, biodiversité, forêts, eau et gestion des ressources naturelles |
| **CNRS-SHS** | `84039` | Institut des Sciences Humaines et Sociales (INSHS - CNRS) | Sciences humaines, sociologie, économie, droit et science politique |
| **LIEPP** | `218465` | Laboratoire interdisciplinaire d'évaluation des politiques publiques (Sciences Po) | Évaluation interdisciplinaire des politiques publiques et méthodes mixtes |
| **PSE** | `301309` | Paris School of Economics - École d'économie de Paris | Économie générale, modélisation des politiques publiques et du climat |
| **CEPII** | `110493` | Centre d'études prospectives et d'informations internationales | Économie internationale, commerce mondial, compétitivité |
| **CNRS** | `441569` | Centre National de la Recherche Scientifique | Établissement national de recherche fondamentale |

> [!TIP]
> **Extension par les relecteurs humains** :
> Pour rechercher et ajouter de nouveaux identifiants d'unités de recherche (UMR, EA, instituts), consultez le moteur de recherche d'AuréHAL sur :
> `https://api.archives-ouvertes.fr/ref/structure/?q=NOM_OU_ACRONYME&wt=json&fl=docid,name_s,acronym_s`
> ou directement l'interface web : [aurehal.hal.science](https://aurehal.hal.science).

---

## 4. Commandes CLI `csc hal`

- `uv run csc hal search "taxe carbone" --proximity "taxe,carbone,3"`
- `uv run csc hal structure IPP --query "carbone"`
- `uv run csc hal get halshs-00557065`
- `uv run csc hal structures`
