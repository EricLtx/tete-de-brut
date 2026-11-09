---
mandat: F030
titre: Base SQLite en WAL, lectures sans verrou d'écriture, connexion et schéma préparés une fois
statut: go
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: préalable de S21 (revue d'architecture du 09/11)
branche: fix/service-base-wal
worktree: .claude/worktrees/fix-service-base-wal
modele: sonnet
effort: high
relecteur: opus / high (concurrence et intégrité des données)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F030 — Base en WAL, lectures sans verrou d'écriture

Constat de la revue d'architecture du 09/11 (dossier privé) : toutes les lectures de `app/base.py` ouvrent `BEGIN IMMEDIATE` (verrou d'écriture), une connexion et la création des tables ont lieu à chaque appel, le journal est en mode `delete` ; mesuré, une lecture échoue en `database is locked` après 5,5 s pendant une écriture longue. Aucun changement de contrat ni de comportement visible.

## Objectif

`journal_mode=WAL` et `busy_timeout` posés à l'ouverture ; schéma créé une fois au démarrage ; lectures en transaction différée (aucun verrou d'écriture) ; écritures et `Transaction` (F023) inchangées dans leur sémantique (`BEGIN IMMEDIATE`). Le mode enregistré et les tests sur base temporaire continuent de marcher.

## Fichiers réservés

`02_Service/app/base.py`, `02_Service/app/main.py` (`lifespan` : préparation du schéma, seulement si nécessaire), `02_Service/tests/test_base.py`.

## Critère de fin

Test : une lecture aboutit pendant qu'une écriture tient sa transaction (deux connexions, fil d'exécution) ; `PRAGMA journal_mode` vaut `wal` ; le schéma n'est pas recréé à chaque appel (compteur ou espion) ; suite complète verte sans modifier les assertions existantes.

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"
gh run list --branch fix/service-base-wal --limit 1   # completed success
```

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernière ligne de pytest ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-09 | orchestrateur | Doublage de 4630a3e : GO avec un majeur hors réserve (`.gitignore` sans `*.sqlite-wal`, `*.sqlite-shm`) ; réserve élargie à `.gitignore` et correctif dans la branche. Doublage de 02eb02b : GO. |
