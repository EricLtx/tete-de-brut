# Registre de la documentation

> Inventaire de chaque document de `01_Docs/` : à quoi il sert, pour qui, et s'il faut le tenir à jour. Une ligne par fichier.
> Dernière mise à jour : 09/11/2026.

## 1. Documents

| Domaine | Document | Rôle | Public | Cycle de vie | Sources dont il dépend |
|---|---|---|---|---|---|
| 00_Index | [README](README.md) | Index et règles de tenue | Tous | Vivant | Ce registre |
| 00_Index | [registre-decisions](registre-decisions.md) | Liste et statut des ADR | Tous | Vivant | `07_Decisions/` |
| 00_Index | [registre-documentation](registre-documentation.md) | Inventaire de la documentation | Tous | Vivant | `01_Docs/` |
| 04_CICD | [pipeline-cicd](../04_CICD/pipeline-cicd.md) | Pipeline locale, gardes, workflow GitHub, règles d'efficience des mandats | Technique | Vivant | `04_Pipeline/`, `config/harnais.json`, `.github/workflows/pipeline.yml` |
| 05_Integration | [branchement-lovable-et-oriane](../05_Integration/branchement-lovable-et-oriane.md) | Guide de branchement des écrans Lovable (adresse unique, routes des cinq gestes, mode et enveloppe d'erreur, CORS, clé de démonstration) et d'Oriane (clé, relevés H01, délai, plafond) | P1, P2, P4 | Vivant | Plan du service, contrat `api.v1` dès S02 |
| 07_Decisions | [0001-perimetre-et-pile-du-service](../07_Decisions/0001-perimetre-et-pile-du-service.md) | ADR-0001 (Acceptée le 07/11/2026) : trois écrans, un cas réel, service d'API dans ce dépôt public, écrans Lovable sur son contrat, transcriptions d'Oriane, SQLite, mode enregistré | Équipe | Acceptée | Transposée de l'ADR-0005 du dépôt privé de cadrage |
| 08_Plans | [plan-service-demonstration](../08_Plans/plan-service-demonstration.md) | Plan de construction du service : fiches S01 à S20, vagues, contrat d'API et compléments, ordre de renoncement ; lot 2 (fiches S21 à S39, pipeline de recherche à phases) ; lot 3 (fiches S40 à S59, versions rapprochées et intendance des transcriptions) | Équipe, orchestrateur | Vivant | ADR-0001, ADR-0003, ADR-0004, plan de construction du dépôt privé |
| 03_Ecrans | [README](../../03_Ecrans/README.md) | Kit des trois écrans Lovable : brief écran par écran sur `api.v1`, `AGENTS.md`, exemples JSON validés, prompts de mode Plan (S11, mandat F011) | P2, orchestrateur | Vivant | Contrat `api.v1`, guide de branchement |
| 07_Decisions | [README](../07_Decisions/README.md) | Règles et gabarit des ADR | Tous | Stable | — |
| 07_Decisions | [0002-fournisseur-du-modele-de-langue](../07_Decisions/0002-fournisseur-du-modele-de-langue.md) | ADR-0002 : Claude comme fournisseur du résumé de fiche (S10) | Orchestrateur | Vivant | ADR-0001 |
| 07_Decisions | [0003-pipeline-de-recherche-a-phases](../07_Decisions/0003-pipeline-de-recherche-a-phases.md) | ADR-0003 (Proposée le 09/11/2026) : pipeline de recherche à phases, machine à états suivie par l'écran Recherche, contrat `execution.v1`, routage des modèles Anthropic | Orchestrateur, propriétaire | Vivant | ADR-0001, ADR-0002, rapport de veille « Pipeline de recherche vidéo journalistique » (dépôt privé) |
| 07_Decisions | [0004-versions-rapprochees-et-intendance-des-transcriptions](../07_Decisions/0004-versions-rapprochees-et-intendance-des-transcriptions.md) | ADR-0004 (Proposée le 09/11/2026) : versions rapprochées et écarts de provenance constatés, intendance des transcriptions, ontologie v2 et raccord aux règles de confiance | Orchestrateur, propriétaire | Vivant | ADR-0001, ADR-0002, ADR-0003, rapport de veille « Pipeline de recherche vidéo journalistique » et relevé « Oriane et Brut » (dépôt privé) |
| 08_Plans | [README](../08_Plans/README.md) | Liste des plans | Tous | Vivant | `08_Plans/` |
| 08_Plans | [modele-plan](../08_Plans/modele-plan.md) | Gabarit de plan | Tous | Stable | — |

Cycles de vie : Vivant (tenu à jour), Stable (change rarement), Figé (historique, ne pas modifier), Archivé.
