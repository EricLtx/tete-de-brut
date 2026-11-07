# Registre de la documentation

> Inventaire de chaque document de `01_Docs/` : à quoi il sert, pour qui, et s'il faut le tenir à jour. Une ligne par fichier.
> Dernière mise à jour : 07/11/2026.

## 1. Documents

| Domaine | Document | Rôle | Public | Cycle de vie | Sources dont il dépend |
|---|---|---|---|---|---|
| 00_Index | [README](README.md) | Index et règles de tenue | Tous | Vivant | Ce registre |
| 00_Index | [registre-decisions](registre-decisions.md) | Liste et statut des ADR | Tous | Vivant | `07_Decisions/` |
| 00_Index | [registre-documentation](registre-documentation.md) | Inventaire de la documentation | Tous | Vivant | `01_Docs/` |
| 04_CICD | [pipeline-cicd](../04_CICD/pipeline-cicd.md) | Pipeline locale, gardes, workflow GitHub, règles d'efficience des mandats | Technique | Vivant | `04_Pipeline/`, `config/harnais.json`, `.github/workflows/pipeline.yml` |
| 07_Decisions | [0001-perimetre-et-pile-du-service](../07_Decisions/0001-perimetre-et-pile-du-service.md) | ADR-0001 (Acceptée le 07/11/2026) : trois écrans, un cas réel, service d'API dans ce dépôt public, écrans Lovable sur son contrat, transcriptions d'Oriane, SQLite, mode enregistré | Équipe | Acceptée | Transposée de l'ADR-0005 du dépôt privé de cadrage |
| 08_Plans | [plan-service-demonstration](../08_Plans/plan-service-demonstration.md) | Plan de construction du service : fiches S01 à S10, vagues, contrat d'API et compléments, ordre de renoncement | Équipe, orchestrateur | Vivant | ADR-0001, plan de construction du dépôt privé |
| 07_Decisions | [README](../07_Decisions/README.md) | Règles et gabarit des ADR | Tous | Stable | — |
| 08_Plans | [README](../08_Plans/README.md) | Liste des plans | Tous | Vivant | `08_Plans/` |
| 08_Plans | [modele-plan](../08_Plans/modele-plan.md) | Gabarit de plan | Tous | Stable | — |

Cycles de vie : Vivant (tenu à jour), Stable (change rarement), Figé (historique, ne pas modifier), Archivé.
