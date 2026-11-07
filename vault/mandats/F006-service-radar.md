---
mandat: F006
titre: S05 — Radar des récits : regroupement par phrase surveillée, mesures de volume avec méthode et fenêtre, plus ancienne version, non cherché, GET /v1/radar et /v1/recits/{id}
statut: en-doublage
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S05
branche: feat/service-radar (part de feat/service-contrats à 407a5c7 ; fusion après S02)
worktree: .claude/worktrees/feat-service-radar
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T10:52Z
rendu_a: 2026-11-07T11:04Z
go_a:
allers_retours: 1
---

# F006 — S05, radar des récits

Le mandat renvoie à la fiche S05 du plan (règle de regroupement fixée là, aucun jugement laissé au réalisateur) et aux modèles `recit.v1` et `mesure` de S02. Il ne les recopie pas.

## Objectif

Le radar se calcule sur les vidéos `video.v1` présentes en base : un récit par phrase surveillée, ses vidéos, ses mesures (conversations observées : vidéos, comptes distincts, vues cumulées « selon Oriane », sur la fenêtre de la requête ; échantillon ; plus ancienne version retrouvée), ce qui n'a pas été cherché ; `GET /v1/radar` et `GET /v1/recits/{id}` servent ces récits avec requête en clair, date du calcul, mode.

## Ce que S02 fournit (b90aaf6)

Imports : `app.modeles` → `Recit`, `Mesure`, `Fenetre`, `Echantillon`, `PlusAncienneVersion`, `Radar`, `Video`, `RECIT_V1`, `LIBELLE_PLUS_ANCIENNE_VERSION` ; `app.libelles` ; `app.base` → `lister`, `lire`, `ecrire`. Contraintes des modèles : une `Mesure` de valeur nulle exige une `raison` ; `methode` et `fenetre` obligatoires ; `enregistre_le` obligatoire en mode `enregistre`. Fixtures : `video_simulee` / `fabriquer_video` (champ `requetes_trouvees`). `GET /v1/radar` et `GET /v1/recits/{id}` sont dans `app/routes/radar.py` ; `POST /v1/radar/actualiser` est dans `app/routes/etat.py` (S04), ne pas y toucher.

## Fichiers réservés

`02_Service/app/recits.py`, `app/mesures.py`, `app/routes/radar.py` (remplir `GET /v1/radar` et `GET /v1/recits/{id}` ; `POST /v1/radar/actualiser` reste à S04), `tests/test_radar.py`. Les phrases surveillées viennent d'un document `cas` en base ou, à défaut, des `requetes_trouvees` des vidéos (lecture la plus simple, à noter dans les Échanges).

## Règle des contrats

Aucun changement de modèle ni de signature de route n'est attendu : les modèles et les routes viennent de S02. Si `test_openapi_egal_au_contrat` échoue malgré tout, relancer `python scripts/exporter_contrats.py` et commiter `contrats/` en le déclarant dans les Échanges ; l'orchestrateur relance l'export à la fusion en cas de conflit.

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
| 2026-11-07 | réalisateur sonnet / medium | Rendu 18a2b97 : `app/mesures.py`, `app/recits.py`, `app/routes/radar.py`, `tests/test_radar.py` (+406), run GitHub 42366305259 vert, 119 tests. Écarts : `tests/test_contrats.py` hors réserve (constante `ROUTES_IMPLEMENTEES`, même endroit que S07) ; décorateurs `erreurs(501)` conservés sur `radar.py` pour ne pas changer le contrat exporté (à nettoyer et réexporter plus tard) ; rattachement vidéo-récit par `requetes_trouvees` normalisées ; documents `cas` lus avec les clés `phrases`/`phrase`, `requete`, `fenetre {debut, fin}`, `enregistre_le` (S04 doit aligner son format) ; identifiant `recit-` + sha256[:12] de la phrase normalisée ; `cout_actualisation` à None (S04). Pour S06 : `mesures_du_recit(videos, fenetre, calcule_le)` appelle `mesures_de_volume` ; ajouter les mesures de vitesse après cet appel, `mesures.echantillon_de(videos)` réutilisable. |
| 2026-11-07 | relecteur sonnet / high | GO sur 18a2b97 : 0 bloquant, 1 majeur (conflit `ROUTES_IMPLEMENTEES` avec S07, à unir), 7 mineurs (requête et fenêtre reconstruites sans cas ; cas mal formé fait tomber le radar ; `enregistre_le` = heure du calcul sur base vide ; `vues_cumulees` sous-estime sans le dire ; `erreurs(501)` conservé ; origine et liens absents de `recit.v1` ; tests légers). 119 tests, `TestClient` (uvicorn refusé par le poste). |
| 2026-11-07 | orchestrateur | S07 fusionné avant S05 : raccord demandé au réalisateur (fusion de `main` dans la branche, union de `ROUTES_IMPLEMENTEES`, garde contre un cas mal formé : radar vide avec `non_cherche` plutôt qu'une 500), nouveau sha relu sur le seul diff. |
