# Index de la documentation

> Point d'entrée unique de `01_Docs/`. Ouvrir ce fichier en premier, puis suivre le lien du domaine concerné.
> Dernière mise à jour : 07/11/2026.

## 1. Organisation

| Dossier | Domaine | Contenu | Quand l'ouvrir |
|---|---|---|---|
| [`00_Index/`](.) | Navigation | Cet index, le [registre des décisions](registre-decisions.md), le [registre de la documentation](registre-documentation.md) | Toujours en premier |
| [`04_CICD/`](../04_CICD/) | Pipeline | Conception de la pipeline locale, table contrôles ↔ exigences | Toucher aux scripts ou aux gardes |
| [`07_Decisions/`](../07_Decisions/) | Décisions | ADR (une décision = un fichier) et gabarit | Proposer ou relire une décision |
| [`08_Plans/`](../08_Plans/) | Plans | Plans d'implémentation à aligner en continu | Avant de commencer un chantier |

Dossiers à ajouter selon le projet (même numérotation) : `01_Brief/` (besoin d'origine, figé), `02_Challenge/` (analyses et veilles datées), `03_Architecture/`, `05_Pilotage/`, `06_Exploitation/`.

## 2. Règles de tenue

- Tout nouveau document est inscrit dans le [registre de la documentation](registre-documentation.md) dans le même commit.
- Toute décision structurante a son ADR et sa ligne dans le [registre des décisions](registre-decisions.md).
- Un plan actif est réaligné à chaque étape terminée (journal d'alignement en fin de plan).
- Données de veille datées et sourcées ; tableaux plutôt que prose quand on compare.
