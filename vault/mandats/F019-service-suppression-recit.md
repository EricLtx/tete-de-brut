---
mandat: F019
titre: S16 — Suppression d'un récit : DELETE /v1/recits/{id} retire la phrase surveillée du radar, ses vidéos orphelines et le consigne au journal
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S16
branche: feat/service-recit-suppression (part de main)
worktree: .claude/worktrees/feat-service-recit-suppression
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T15:40Z
rendu_a:
go_a:
allers_retours: 0
---

# F019 — S16, suppression d'un récit

Demande de l'équipe le 07/11 à 16 h 35 : il manque la possibilité de supprimer un récit sur la plateforme. Un récit est la vue d'une phrase surveillée (`app/recits.py` : `identifiant_recit(phrase)`, phrases lues dans les documents du cas et dans les documents ajoutés par une recherche, `app/recherche.py` ligne « Ajoute la phrase aux phrases surveillées »). Le mandat renvoie à `app/recits.py`, `app/recherche.py`, `app/base.py`, `app/securite.py`, `app/main.py`, aux contrats et aux tests ; il ne les recopie pas.

## Objectif

`DELETE /v1/recits/{id}`, derrière `X-Cle-Demo` (l'intergiciel `app/securite.py` exige désormais la clé sur DELETE comme sur POST et PATCH ; CORS `allow_methods` de `app/main.py` ajoute DELETE) : retire la phrase du récit de toutes les listes de phrases surveillées en base (document du cas et documents ajoutés par une recherche), retire cette phrase de `requetes_trouvees` des vidéos, supprime les vidéos dont `requetes_trouvees` devient vide (orphelines), consigne une entrée de journal (`route` « recit:suppression », `cible` la phrase, `resultats` {vidéos retirées, vidéos conservées}), et rend 200 avec `{"mode": …, "enregistre_le": …, "identifiant": …, "phrase_surveillee": …, "videos_retirees": n, "videos_conservees": n}` (modèle `SuppressionRecit`). Récit inconnu : 404 `introuvable`. `GET /v1/radar` et `GET /v1/recits/{id}` ne servent plus le récit. En mode enregistré, la suppression vaut pour la base courante (le fichier du cas sur disque n'est pas modifié ; au redémarrage avec `cas.json` inchangé, la phrase revient : le dire dans la réponse par un champ `avertissement` quand le mode est `enregistre`).

## Fichiers réservés

`app/recits.py` (`supprimer_recit(identifiant)`), `app/base.py` (une fonction `supprimer(type, identifiant)` si elle manque), `app/routes/radar.py` (la route), `app/securite.py` (DELETE sous clé), `app/main.py` (une ligne CORS), `app/modeles.py` (`SuppressionRecit`), `contrats/api.v1.json` (réexport), `tests/test_radar.py`, `tests/test_contrats.py` (`ROUTES_IMPLEMENTEES`), `tests/test_regles_transverses.py` (clé de démo exigée sur DELETE), `tests/test_socle.py` seulement si l'intergiciel y est testé. Rien dans `app/recherche.py` (F018 y travaille en parallèle) : la lecture des documents de phrases se fait par leurs types déjà écrits en base.

## Règles de confiance (testées)

Aucune suppression sans clé de démonstration quand elle est posée ; une vidéo trouvée aussi par une autre phrase est conservée ; le journal porte la suppression ; `mode` partout ; aucun libellé refusé.

## État du poste

Python 3.12 hors PATH (`C:\Users\User\AppData\Local\Programs\Python\Python312`), venv `C:\Users\User\AppData\Local\Temp\claude\venv-f011`. Aucun appel réseau nécessaire.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-recit-suppression --limit 1   # completed success
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; tests ; écarts ; réponse exacte de la route (exemple).

## Échanges

| Date | De | Message |
|---|---|---|
