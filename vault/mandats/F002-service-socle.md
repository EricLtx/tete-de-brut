---
mandat: F002
titre: S01 — Socle du service : configuration par l'environnement, santé, CORS, enveloppe d'erreur, clé de démonstration, magasin SQLite, journal, image de conteneur
statut: fusionne
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S01
branche: feat/service-socle
worktree: .claude/worktrees/feat-service-socle
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T10:05Z
rendu_a: 2026-11-07T10:18Z
go_a: 2026-11-07T10:26Z
allers_retours: 0
---

# F002 — S01, socle du service

Le mandat renvoie à la fiche S01 du plan (tableau « Fiches de tâches », ligne S01, et sous-section « Compléments de contrat ») et à l'ADR-0001 (pile close). Il ne les recopie pas ; tout ce qui n'y figure pas est hors mandat.

## Objectif

Le service démarre sous `02_Service/`, se configure par l'environnement, répond sur `/sante`, n'ouvre CORS qu'aux origines déclarées, pose l'enveloppe d'erreur unique et la clé de démonstration optionnelle, garde ses données dans un magasin SQLite générique avec journal des appels, et se construit en image de conteneur. Aucune route métier : elles viennent de S02.

## Fichiers réservés

Ceux de la fiche S01, sous `02_Service/` : `pyproject.toml`, `.env.example`, `Dockerfile`, `.dockerignore`, `app/__init__.py`, `app/main.py`, `app/config.py`, `app/erreurs.py`, `app/securite.py`, `app/base.py`, `tests/__init__.py`, `tests/conftest.py` (fixtures de base : application de test, base temporaire, variables d'environnement), `tests/test_socle.py`, `cas/.gitignore`, `cas/README.md`. `config/harnais.json → pipeline.build` est déjà renseigné : le vérifier, ne pas le modifier.

## État du poste

Python 3.13 sur le poste (image en 3.12), Docker 29 présent, réseau ouvert, aucune clé Oriane, aucune fixture existante. Versions à figer dans `pyproject.toml` (lues avec `pip index versions`).

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m 'not reel'   # 0 erreur, tests verts
gh run list --branch feat/service-socle --limit 1   # completed success
curl -s localhost:8080/sante   # {"etat":"ok","version":"0.1.0","mode":"enregistre",...} avec le service lancé sans clé
docker build 02_Service   # réussit (H)
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat origin/main...HEAD` ; résultat du run GitHub ; écarts à la fiche ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | réalisateur sonnet / medium | Rendu a6f65b5 : 16 fichiers sous 02_Service/, 32 tests, run GitHub vert (34 s), docker build et /sante vérifiés. Écarts : 02_Service/.gitignore ajouté (egg-info) ; clé de démonstration en intergiciel sous CORS ; avertissement CLE_DEMO vide au journal et au log ; starlette juge httpx déprécié pour TestClient (httpx2 hors pile close, non ajouté). |
| 2026-11-07 | relecteur sonnet / high | GO sur a6f65b5 : 0 bloquant, 0 majeur, 6 mineurs (`.dockerignore` sans `.env`, `startswith("/v1")`, 500 sans CORS ni test, motif `token` dans le filtre de secrets de `base.py`, état global du chemin de base) ; run GitHub vert, 32 tests, service lancé, image construite. Fusionné sur `main` (f2e0a0e). Mineurs transmis à S03 et S08. |
