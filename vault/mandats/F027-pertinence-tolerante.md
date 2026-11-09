---
mandat: F027
titre: Pertinence mal formée tolérée de bout en bout (suite du doublage F023, constat 1)
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S20 (suite)
branche: fix/service-pertinence-tolerante
worktree: .claude/worktrees/fix-service-pertinence-tolerante
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F027 — Pertinence mal formée tolérée

Renvoie au rapport `vault/revues/F023-f916fdd.md`, constat mineur 1 (et, facultatif, constat 2). Aucun changement de contrat.

## Objectif

Une pertinence enregistrée mal formée (trois formes reproduites au doublage) ne fait plus rendre 500 à `GET /v1/radar` ni à `POST /v1/recits/{id}/pertinence` : `calculer_recits` l'ignore pour ce récit (récit rendu sans pertinence) et le journal du service le signale sans contenu de vidéo. Facultatif si sans risque : sortir l'appel au modèle de `_preparer_en_fil` du verrou des crédits dans `recherche.executer` (constat 2).

## Fichiers réservés

`02_Service/app/recits.py`, `02_Service/app/recherche.py` (constat 2 seulement), `02_Service/tests/test_recits.py`, `02_Service/tests/test_pertinence.py`, `02_Service/tests/test_recherche.py` (constat 2 seulement).

## Critère de fin

Un test de route par forme mal formée : 200, récit présent, pertinence absente ; tests existants verts sans modification de leurs assertions.

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"
gh run list --branch fix/service-pertinence-tolerante --limit 1   # completed success
```

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernière ligne de pytest ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
