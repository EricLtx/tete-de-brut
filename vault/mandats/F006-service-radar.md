---
mandat: F006
titre: S05 — Radar des récits : regroupement par phrase surveillée, mesures de volume avec méthode et fenêtre, plus ancienne version, non cherché, GET /v1/radar et /v1/recits/{id}
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S05
branche: feat/service-radar (part de feat/service-contrats rendue ; fusion après S02)
worktree: .claude/worktrees/feat-service-radar
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a:
rendu_a:
go_a:
allers_retours: 0
---

# F006 — S05, radar des récits

Le mandat renvoie à la fiche S05 du plan (règle de regroupement fixée là, aucun jugement laissé au réalisateur) et aux modèles `recit.v1` et `mesure` de S02. Il ne les recopie pas.

## Objectif

Le radar se calcule sur les vidéos `video.v1` présentes en base : un récit par phrase surveillée, ses vidéos, ses mesures (conversations observées : vidéos, comptes distincts, vues cumulées « selon Oriane », sur la fenêtre de la requête ; échantillon ; plus ancienne version retrouvée), ce qui n'a pas été cherché ; `GET /v1/radar` et `GET /v1/recits/{id}` servent ces récits avec requête en clair, date du calcul, mode.

## Fichiers réservés

`02_Service/app/recits.py`, `app/mesures.py`, `app/routes/radar.py` (remplir `GET /v1/radar` et `GET /v1/recits/{id}` ; `POST /v1/radar/actualiser` reste à S04), `tests/test_radar.py`. Les phrases surveillées viennent d'un document `cas` en base ou, à défaut, des `requetes_trouvees` des vidéos (lecture la plus simple, à noter dans les Échanges).

## État du poste

Venv de S01, fixtures de S02 (`video_simulee`, `deux_videos_comparables`), aucun réseau nécessaire.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-radar --limit 1   # completed success
curl -s localhost:8080/v1/radar   # au moins un recit.v1 ; chaque mesure a methode et fenetre ; aucun mot refusé hors citation
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; run et tests ; écarts ; points ouverts pour S06 (ligne d'appel de l'indicateur de vitesse dans `recits.py`).

## Échanges

| Date | De | Message |
|---|---|---|
