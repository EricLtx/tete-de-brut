---
mandat: F004
titre: S02 — Contrats JSON et OpenAPI api.v1, normalisation mots.v1, libellés refusés, routes présentes en 501
statut: fusionne
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S02
branche: feat/service-contrats (part de feat/service-socle rendue ; fusion après celle de S01)
worktree: .claude/worktrees/feat-service-contrats
modele: opus
effort: medium
relecteur: opus / medium (conception du contrat que tous les mandats et les écrans suivent)
cree: 2026-11-07
lance_a: 2026-11-07T10:30Z
rendu_a: 2026-11-07T10:34Z
go_a: 2026-11-07T10:55Z
allers_retours: 1
---

# F004 — S02, contrats du service

Le mandat renvoie à la fiche S02 du plan (ligne S02 du tableau « Fiches de tâches », sous-sections « Contrat d'API attendu » et « Compléments de contrat ») et au guide `01_Docs/05_Integration/branchement-lovable-et-oriane.md` § 2 et § 3. Il ne les recopie pas.

## Objectif

Les contrats partagés par le service et les écrans existent avant tout code métier : modèles pydantic `video.v1`, `recit.v1`, objet `mesure`, `ecart.v1`, `fiche.v1`, `decision.v1` (champs en français `snake_case`), normalisation `mots.v1`, filtre des libellés refusés sur les segments `libelle`, routes de `api.v1` présentes sous `/v1` et répondant 501 dans l'enveloppe, schémas JSON et `contrats/api.v1.json` exportés et égaux à ce que sert l'application.

## Fichiers réservés

Ceux de la fiche S02, sous `02_Service/` : `app/modeles.py`, `app/mots.py`, `app/libelles.py`, `app/routes/__init__.py`, `app/routes/etat.py`, `app/routes/radar.py`, `app/routes/videos.py`, `app/routes/comparaisons.py`, `app/routes/fiches.py`, `app/main.py` (branchement des routeurs seulement, dernier mandat à le toucher), `contrats/*.schema.json`, `contrats/api.v1.json`, `scripts/exporter_contrats.py`, `tests/test_contrats.py`, `tests/conftest.py` (ajout de fixtures de vidéos simulées réutilisables, sans retirer celles de S01).

## État du poste

Python 3.13, venv `02_Service/.venv` créé par S01, fixtures `client`, `client_avec_cle`, `config_test` de S01, aucune clé Oriane, réseau ouvert.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m 'not reel'   # vert
python scripts/exporter_contrats.py --verifier   # 0 : contrats/ égal à l'application
gh run list --branch feat/service-contrats --limit 1   # completed success
curl -s localhost:8080/v1/radar   # 501 {"erreur":"non_implemente",...}
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat feat/service-socle...HEAD` ; résultat du run GitHub et nombre de tests ; écarts à la fiche ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | réalisateur opus / medium | Rendu b90aaf6 : 19 fichiers, +4589, run GitHub 42364385279 vert, 103 tests (32 S01 + 71 S02), `/openapi.json` égal à `contrats/api.v1.json`. Écarts : `main.py` reçoit aussi titre, version `api.v1` et `/sante` hors schéma ; `POST /v1/radar/actualiser` dans `routes/etat.py` (réservé à S04) ; `GET /v1/journal?limite=` ; `POST /v1/fiches` 201 ; contraintes plus strictes (mesure nulle exige raison, fiche exige segment LIMITE_TRANSCRIPTIONS, `enregistre_le` obligatoire en mode enregistré) ; `Etat` n'hérite pas de `Reponse`. Règle pour S03 à S08 : tout mandat qui change un modèle ou une route relance `scripts/exporter_contrats.py` et commite `contrats/`. |
| 2026-11-07 | relecteur opus / medium | GO conditionnel sur b90aaf6 : 0 bloquant, 1 majeur (`mots.py` supprime la virgule et le point entre deux chiffres : « 3,5 milliards » = « 35 milliards », contraire à « nombres gardés tels que transcrits », cas D), 10 mineurs ; run GitHub vert, 103 tests, export identique, 401/404/422 vérifiés en direct. |
| 2026-11-07 | orchestrateur | Majeur non reporté : correctif sur la même branche par le réalisateur (constats 1, 2, 8, 11 : séparateur décimal gardé entre deux chiffres, libellés refusés aussi sans accent, règles de `mots.v1` décrites dans le contrat, double NFC retirée), nouveau sha, relecture du seul diff par le même relecteur. Constat 6 (deux fenêtres) tranché avant S06 ; constat 7 (liens et origine du récit) consigné au plan. |
| 2026-11-07 | relecteur opus / medium | GO sur 407a5c7 (correctif relu sur le seul diff) : 0 bloquant, 0 majeur, 9 mineurs dont deux nouveaux (description de `normalisation` muette sur les symboles et les espaces Unicode ; « 3,5 » et « 3.5 » restent deux mots, « faux-semblant » refusé dans un libellé). 111 tests, run 42365615589 vert. Fusionné sur `main`. |
