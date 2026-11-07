---
mandat: F007
titre: S07 — Écart au mot entre deux vidéos sur la normalisation mots.v1, POST /v1/comparaisons idempotent et GET /v1/comparaisons/{id}
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S07
branche: feat/service-ecart (part de feat/service-contrats rendue ; fusion après S02)
worktree: .claude/worktrees/feat-service-ecart
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a:
rendu_a:
go_a:
allers_retours: 0
---

# F007 — S07, écart au mot

Le mandat renvoie à la fiche S07 du plan, au complément de contrat e (idempotence) et au modèle `ecart.v1` de S02. Il ne les recopie pas.

## Objectif

Deux vidéos présentes en base sont comparées mot à mot (distance d'édition par programmation dynamique en Python standard sur `mots.v1`, opérations retiré, ajouté, remplacé avec positions), ainsi que leurs légendes et textes à l'écran, sans aucun champ de qualification ; l'identifiant de la comparaison dérive des deux identifiants de vidéo (même couple, même ressource, 200 à la seconde demande) ; heure dans la vidéo « non fournie au niveau default ».

## Fichiers réservés

`02_Service/app/ecart.py`, `app/routes/comparaisons.py` (remplir les deux routes de S02), `tests/test_ecart.py`.

## État du poste

Venv de S01, fixture `deux_videos_comparables` de S02, aucun réseau.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert ; 600 contre 150 mots en moins de 0,5 s
gh run list --branch feat/service-ecart --limit 1   # completed success
curl -s -X POST localhost:8080/v1/comparaisons -H "Content-Type: application/json" -d "{\"video_source\":\"…\",\"video_reprise\":\"…\"}"   # ecart.v1, normalisation = mots.v1, transcriptions attribuées à Oriane
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; run et tests ; écarts ; points ouverts pour S08 (forme des opérations à afficher dans la fiche).

## Échanges

| Date | De | Message |
|---|---|---|
