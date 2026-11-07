---
mandat: F008
titre: S04 — Modes direct et enregistré, actualisation du radar, état et journal, script d'enregistrement du cas avec la clé
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S04
branche: feat/service-modes (part de main après fusion de S03, S05 et S07)
worktree: .claude/worktrees/feat-service-modes
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T11:55Z
rendu_a:
go_a:
allers_retours: 0
---

# F008 — S04, modes et cas enregistré

Le mandat renvoie à la fiche S04 du plan, aux compléments de contrat b, d et f, et aux rendus de S03 (`app/oriane.py`, `ResultatRecherche`, exceptions `OrianeInjoignable`, `CreditsEpuises`, `RequeteInvalide`) et S05 (`app/recits.py`, lecture des documents `cas`). Il ne les recopie pas.

## Objectif

Le service obtient les vidéos du cas en direct (`actualiser()` appelle `rechercher` de S03 pour les phrases du cas) ou depuis le cas enregistré, bascule seul en `enregistre` (deux expirations de suite, 402, plafond `PLAFOND_CREDITS_JOUR` atteint, ou `MODE_DONNEES=enregistre`) et l'annonce avec sa raison ; `POST /v1/radar/actualiser` déclenche une acquisition et rend le coût estimé ; `GET /v1/etat` porte mode, raison, `enregistre_le`, crédits du jour sur plafond, `version`, `contrat` ; `GET /v1/journal` sert le journal ; un humain enregistre le cas avec sa clé par `scripts/enregistrer_cas.py`.

## Ce que S03 et S05 fournissent

S03 : `rechercher(...)` asynchrone, rend `ResultatRecherche` (videos, total, ecartees, code, credits_estimes, requete, incomplete), écrit les vidéos en base ; exceptions sans gestionnaire d'enveloppe (à poser ici dans `app/erreurs.py` : `OrianeInjoignable` → 503 `oriane_injoignable` avec raison, `CreditsEpuises` → 503 `credits_epuises`, `RequeteInvalide` → 422 `validation`). S05 : les documents de type `cas` en base sont lus avec `phrases` (liste) ou `phrase`, `requete`, `fenetre {debut, fin}`, `enregistre_le` ; c'est le format à produire ici (une seule source de vérité : définis-le dans `app/cas.py` et fais-le relire par S05 si besoin). La route `GET /v1/videos/{id}` pose `mode` direct seulement si la vidéo a été écrite en direct.

## Format du cas enregistré (`CHEMIN_CAS`, hors Git)

Un fichier JSON : `{"enregistre_le": ISO, "projection": "default", "credits_estimes": n, "phrases": [...], "comptes": [...], "fenetre": {"debut", "fin"}, "requete": "<requête en clair>", "videos": [video.v1, ...]}`. Chaque vidéo est validée contre `video.v1` au chargement ; un champ de tiers, une vidéo ou une image font refuser le fichier. Le script refuse d'écrire si un champ refusé subsiste. `02_Service/cas/.gitignore` et `cas/README.md` existent déjà (S01).

## Fichiers réservés

`02_Service/app/acquisition.py`, `app/cas.py`, `scripts/enregistrer_cas.py`, `app/routes/etat.py` (remplir `POST /v1/radar/actualiser`, `GET /v1/etat`, `GET /v1/journal`), `app/erreurs.py` (ajout des trois gestionnaires seulement), `app/config.py` (ajout de `PLAFOND_CREDITS_JOUR`, défaut 600, et `CHEMIN_CAS` si absent), `.env.example`, `tests/test_acquisition.py`, `tests/conftest.py` (ajout d'une fixture `cas_simule`), `tests/test_contrats.py` (constante `ROUTES_IMPLEMENTEES` : y ajouter les trois routes ; retirer `erreurs(501)` des routes remplies par S03, S05, S07 et ici, et réexporter `contrats/` en le déclarant).

## Règle des contrats

Ce mandat retire le 501 documenté des routes remplies : relancer `python scripts/exporter_contrats.py`, commiter `contrats/`, et adapter `test_openapi_titre_version_et_erreur` (501 attendu seulement sur les routes encore en 501 : celles de S08).

## État du poste

Venv à créer dans le worktree ; fixtures de S01 à S03 (`client`, `video_simulee`, `reponse_oriane_simulee`, `transport_oriane_simule`) ; aucune clé en test, aucun réseau.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-modes --limit 1   # completed success
curl -s localhost:8080/v1/etat   # mode enregistre sans clé, raison, enregistre_le, credits_jour/plafond, version, contrat = api.v1
```

Règle RG-02 de la fiche S03, reportée ici (majeur du doublage de F005) : une phrase surveillée réduite à un nom de personne est refusée ; en l'absence de détection de noms, la règle codée est « moins de trois mots → refusée avec raison », dans `enregistrer_cas.py` et dans `actualiser()`, testée.

Tests exigés : deux expirations simulées → `mode` `enregistre`, raison « Oriane injoignable » ; plafond atteint → aucun appel parti ; 402 → bascule et raison ; le script refuse un cas contenant `popularComments` ; `MODE_DONNEES=enregistre` force le mode même avec clé ; `POST /v1/radar/actualiser` sans clé de démo → 401 quand `CLE_DEMO` est posée ; un résultat enregistré n'est jamais servi avec `mode` `direct`.

## Compte rendu attendu (cinq lignes)

sha ; diff ; run et tests ; écarts ; points ouverts pour H03 (commande exacte du script, format du fichier de requêtes).

## Échanges

| Date | De | Message |
|---|---|---|
