---
mandat: F029
titre: Tolérance aux pertinences mal formées étendue aux lectures restantes (suites du doublage F027)
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S20 (suite)
branche: fix/service-tolerance-lectures
worktree: .claude/worktrees/fix-service-tolerance-lectures
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F029 — Tolérance étendue aux lectures restantes

Renvoie au rapport `vault/revues/F027-cac284e.md`, constats mineurs 1 à 3. Aucun changement de contrat.

## Objectif

Une vidéo dont la pertinence enregistrée est mal formée ne fait plus rendre 500 nulle part : `GET /v1/videos/{id}`, fiches, comparaisons, rejeu d'un récit en mode enregistré (`_recit_rejoue`) passent par `recits.lire_videos` ; `supprimer_recit` est couvert par un test ; `POST /v1/recits/{id}/pertinence` rejuge une vidéo à pertinence mal formée au lieu de l'ignorer.

## Fichiers réservés

`02_Service/app/recits.py`, `app/recherche.py` (`_recit_rejoue` seulement), `app/routes/videos.py`, `app/routes/fiches.py`, `app/routes/comparaisons.py`, `app/routes/pertinence.py`, `tests/test_videos.py`, `tests/test_fiches.py`, `tests/test_comparaisons.py`, `tests/test_pertinence.py`, `tests/test_recherche.py`, `tests/test_suppression.py` (ou le fichier de test de la suppression existant).

## Critère de fin

Un test de route par lecture listée (forme mal formée : 200, vidéo présente sans pertinence) ; la mutation qui retire la tolérance de `supprimer_recit` fait échouer un test ; la vidéo fautive est rejugée par la route de pertinence ; tests existants inchangés.

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"
gh run list --branch fix/service-tolerance-lectures --limit 1   # completed success
```

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernière ligne de pytest ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
