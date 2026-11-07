---
mandat: F004
branche: feat/service-contrats
commit: 407a5c72a19c2c4914168cb5e3121b66f8f47b54
relecteur: sonnet
effort: high
verdict: GO
date: 2026-11-07
---

# Doublage F004 (relecteur de la config) — S02, contrats du service

## Verdict

GO : j'ai rejoué moi-même tous les contrôles sur 407a5c7 (111 tests, lint, export, 13 routes en 501, `mots.v1` corrigé) et je confirme les deux relectures `opus` (b90aaf6 puis 407a5c7) : le majeur de la première est bien levé, aucun bloquant ni majeur ne subsiste.

## Constats

| # | Gravité | Emplacement | Constat | Remède |
|---|---|---|---|---|
| 1 | mineur | `02_Service/app/routes/` (`POST /v1/comparaisons`, `POST /v1/fiches`, `POST /v1/fiches/{id}/decision`) | Avec un corps vide, ces trois routes rendent 422 `validation` et non 501, car le corps est validé avant le gestionnaire. Avec un corps valide, 501. Cohérent avec le contrat (pydantic d'abord), mais un curl sans corps ne montre pas le 501. | Aucun ; tester avec un corps valide. |
| 2 | mineur | cohérence avec les rapports opus | Les mineurs 3, 4, 5, 6, 7, 10, 12 et 13 des rapports `F004-b90aaf6` et `F004-407a5c7` sont toujours ouverts, tels que décrits (`Erreur.erreur` en `str`, filtre limité aux segments `libelle`, `mode` hérité, une fenêtre par mesure, liens et origine du récit, description de `normalisation` muette sur symboles et espaces Unicode). Aucun n'est un majeur. 6 et 7 sont consignés au plan (journal du 07/11). Je n'ai rien trouvé qui contredise les deux rapports. | Voir les rapports opus ; 3 et 12 au prochain changement de contrat. |

Aucun bloquant, aucun majeur. Le majeur du premier passage (« 3,5 » = « 35 ») est corrigé et testé.

## Vérifications faites

| Vérification | Commande | Résultat |
|---|---|---|
| Sha relu | `git rev-parse HEAD` ; `git rev-parse origin/feat/service-contrats` | identiques : `407a5c72a19c2c4914168cb5e3121b66f8f47b54` |
| Run GitHub | `gh run list --branch feat/service-contrats --limit 1 --json conclusion,headSha` | `success`, `headSha` = sha relu |
| Lint | `.venv/Scripts/python -m ruff check .` ; `ruff format --check .` | « All checks passed! » ; 21 fichiers déjà formatés |
| Tests | `python -m pytest -q -m "not reel"` (Python 3.13.14) | 111 passés, 1 avertissement (dépréciation httpx/starlette), 1,94 s |
| Export | `python scripts/exporter_contrats.py --verifier` | « contrats à jour », code 0 |
| Commits | `git log --oneline a6f65b5..HEAD` | 2 commits typés : `feat(service)` b90aaf6, `fix(service)` 407a5c7 |
| Périmètre | `git diff --stat a6f65b5...HEAD` ; `git diff --name-only … \| grep -v '^02_Service/'` | 19 fichiers, +4647 / −5, tous sous `02_Service/` et dans la réserve ; aucun fichier de garde, de config du harnais ni de registre |
| `main.py` | `git diff a6f65b5...HEAD -- 02_Service/app/main.py` | `include_router` des 5 modules sous `/v1`, titre, `version=API_V1`, `/sante` avec `include_in_schema=False` ; rien d'autre. Écart déclaré, accepté |
| `conftest.py` | `git diff … -- tests/conftest.py` ; liste des `def` avant et après | ajouts seulement (une ligne d'import remplacée par une plus large) ; `config_test`, `client`, `client_avec_cle`, `construire_config` de S01 intacts |
| Courriels | `git grep -nIE '[[:alnum:]._%+-]+@[[:alnum:].-]+[.][[:alpha:]]{2,}'` | vide (code 1) |
| Secrets | `git grep -nIiE` clé/secret/jeton/mot de passe avec valeur littérale ; noms Oriane (`platformId`, `publishedAt`, `onScreenText`, `"transcript"`) dans `app/` et `contrats/` | rien (hors fixtures de test S01 `secret-de-test`) ; aucun nom Oriane |
| Service en direct | `CLE_DEMO=cle-revue python -m uvicorn app.main:creer_application --factory --port 8084` ; `GET /sante` | 200 `{"etat":"ok","version":"0.1.0","mode":"enregistre","enregistre_le":null}` |
| 13 routes en 501 | `curl` des 13 opérations de `/v1` (12 chemins) avec la clé et un corps valide pour les POST | toutes 501 `{"erreur":"non_implemente","detail":…,"mode":"enregistre"}` ; `contrats/api.v1.json` compte 13 opérations, toutes sous `/v1` |
| 404, 401, 422 | `GET /v1/inconnue` ; `GET /radar` ; `POST /v1/comparaisons` sans clé ; avec corps vide | 404 `introuvable` (deux fois) ; 401 `cle_demo_invalide` ; 422 `validation` dans l'enveloppe (constat 1) |
| OpenAPI servi | `GET /openapi.json` comparé en JSON à `contrats/api.v1.json` | égal |
| Arrêt du service | arrêt des deux processus uvicorn ; `GET /sante` | plus de réponse, aucun processus restant sur 8084 |
| `mots.v1` | `normaliser("3,5 milliards")` et `normaliser("35 milliards")` | `['3,5','milliards']` ≠ `['35','milliards']` (différents) |
| Rapports opus | lecture des deux rapports et du mandat (Échanges) | cohérents avec ce que j'observe : sha, 111 tests, export, périmètre, correctif du majeur ; aucun constat majeur non corrigé |
| Propreté | `git status --short` à la fin | vide ; seuls les dossiers ignorés (`.venv`, caches) restent |

## Mandats de suite

Aucun mandat bloquant. Constats 3 et 12 des rapports opus au prochain changement de contrat ; constat 6 tranché avant S06 (plan : deux mesures, `mesure` inchangée) ; constat 7 reporté après le hackathon (plan).

Non vérifié : pipeline locale `04_Pipeline/ci.sh --ref` (le run GitHub fait foi, voir la mémoire du projet) ; relecture ligne à ligne de `modeles.py` et des 2157 lignes de `api.v1.json` (contrôlés par le test d'égalité et les sondes des deux passages opus).
