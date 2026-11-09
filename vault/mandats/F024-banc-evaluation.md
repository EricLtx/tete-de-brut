---
mandat: F024
titre: S22 — Banc d'évaluation rejouable sans réseau (jeu.v1, rappel@k, nDCG@k, faits couverts)
statut: fusionne
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S22
branche: feat/service-banc-evaluation
worktree: .claude/worktrees/feat-service-banc-evaluation
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F024 — S22, banc d'évaluation

Renvoie à la fiche S22 du plan (lot 2) ; aucun changement de contrat (`02_Service/contrats/` intouché), aucun fichier de `app/` modifié.

## Objectif

Un jeu de questions au format `jeu.v1` se rejoue contre le bras `unique` (`POST /v1/recherches` actuel) et donne un rapport en comptes : rappel@k, nDCG@k, part des faits couverts, crédits, jetons, latence. Les bras `multi` et `boucle` sont déclarés et refusés proprement (« disponible à partir de S29 »).

## Fichiers réservés

Ceux de la fiche S22, chemins relatifs à `02_Service/` ; `evaluation/README.md` inscrit au registre de la documentation (une ligne, `01_Docs/00_Index/registre-documentation.md`). Réponses Oriane simulées de `tests/conftest.py` réutilisées, jamais redéfinies.

## Critère de fin

Rappel@k et nDCG@k exacts sur des listes connues ; un jeu mal formé est refusé ; le dossier de données du banc est ignoré par Git ; un jeu simulé de trois questions contre `TestClient` donne un rapport lisible, sans réseau.

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"
gh run list --branch feat/service-banc-evaluation --limit 1   # completed success
```

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernière ligne de pytest ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
