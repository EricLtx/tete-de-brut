---
mandat: F003
titre: Licence commerciale « Tête de Brut. » (co-auteurs) et LICENSE en documentation seule
statut: realise
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: hors fiche (décision du propriétaire du 07/11/2026)
branche: chore/licence
worktree: aucun (deux fichiers, orchestrateur ; écart déclaré)
modele: orchestrateur
effort: low
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T10:00Z
rendu_a: 2026-11-07T10:03Z
go_a:
allers_retours: 0
---

# F003 — Licence du dépôt public

## Objectif

Le dépôt porte un fichier `LICENSE` : licence commerciale « Tête de Brut. », droits réservés aux co-auteurs tels qu'ils figurent dans l'historique des contributions, lecture et exécution locale permises, toute réutilisation soumise à accord écrit. `LICENSE` rejoint `docsSeulement` pour pouvoir évoluer sans doublage.

## Fichiers réservés

`LICENSE`, `config/harnais.json` (clé `docsSeulement` seulement).

## Commande de fin et sortie attendue

```bash
git diff --stat origin/main...chore/licence   # deux fichiers
python -c "import json;d=json.load(open('config/harnais.json',encoding='utf-8'));print('LICENSE' in d['docsSeulement'])"   # True
gh run list --branch chore/licence --limit 1   # completed success
```

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | orchestrateur | Décision du propriétaire : « Licence Commerciale Tête de Brut. (Co-auteurs) ». Aucun nom de personne dans le fichier : les co-auteurs sont désignés par l'historique Git. |
