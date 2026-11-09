---
mandat: F026
titre: Kit et documentation réalignés sur quatre écrans (suites du doublage F017)
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S14 (suites)
branche: fix/ecrans-kit-quatre-ecrans
worktree: .claude/worktrees/fix-ecrans-kit-quatre-ecrans
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F026 — Kit à quatre écrans, suites de F017

Renvoie au rapport `vault/revues/F017-5ca7666.md` : constats mineurs 1, 2, 3 et hors périmètre H1 à H5. Le constat 4 se garde tel quel. Aucun changement de contrat ni de `app/`.

## Objectif

Un projet Lovable qui suit les prompts du kit dans l'ordre ne reçoit plus aucune consigne contradictoire : quatre routes partout (`/` Recherche, `/radar` Radar), retour au radar vers `/radar`, exemples raccordés au même récit, accord « 1 filtre », `filtres.comptes` affiché, exemples de suppression et de pertinence joints au prompt 04 avec ce que l'écran `/` affiche après suppression, règle des données d'essai clarifiée pour les routes servies en 200 ou 201, guide d'intégration § 2 et `README.md` racine à quatre écrans, ligne `03_Ecrans` du registre de la documentation.

## Fichiers réservés

`03_Ecrans/prompts/00-projet.md`, `02-versions.md`, `03-fiche.md`, `04-recherche.md`, `03_Ecrans/README.md`, `03_Ecrans/AGENTS.md` (sous 10 000 octets), `03_Ecrans/exemples/suppression-recit.json`, `pertinence-recit.json`, `README.md` (racine), `01_Docs/00_Index/registre-documentation.md` (ligne `03_Ecrans` seulement), `01_Docs/05_Integration/` § 2, `02_Service/tests/test_exemples_ecrans.py`. Le plan n'est pas touché (orchestrateur).

## Critère de fin

`git grep -n "trois routes\|trois écrans"` ne rend que le plan et l'historique figé (mandats, revues) ; un test vérifie que les identifiants de récit des exemples de suppression et de pertinence existent dans `radar.json` ou `recherche-executee.json`.

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"
gh run list --branch fix/ecrans-kit-quatre-ecrans --limit 1   # completed success
```

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernière ligne de pytest ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
