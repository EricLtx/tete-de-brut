---
mandat: F005
titre: S03 — Adaptateur Oriane : une seule fonction d'appel, liste blanche des champs vers video.v1, journal de chaque appel, GET /v1/videos/{id}
statut: realise
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S03
branche: feat/service-oriane (part de feat/service-contrats à 407a5c7 ; fusion après S02)
worktree: .claude/worktrees/feat-service-oriane
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T10:52Z
rendu_a: 2026-11-07T11:07Z
go_a:
allers_retours: 1
---

# F005 — S03, adaptateur Oriane

Le mandat renvoie à la fiche S03 du plan et aux modèles `video.v1` de S02 (`app/modeles.py`, `contrats/video.v1.schema.json`). Il ne les recopie pas.

## Objectif

Une seule fonction appelle Oriane avec les filtres de la fiche, ne laisse passer que les champs de `video.v1` (liste blanche, champs de tiers refusés), journalise chaque appel sans réponse brute ni clé, et `GET /v1/videos/{id}` sert une vidéo écrite en base.

## Faits Oriane (spécification OpenAPI relevée le 04/11, F)

Base `https://connect.oriane.xyz` (`ORIANE_URL`, défaut à poser) ; `POST /rest/contents/search?sort=publishedAt:asc&offset=0&limit=100&projection=default` ; corps `{"name": "...", "operator": "and", "filters": {...}, "queries": [...]}` ; filtres `transcript` et `onScreenText` : `{"includesExactly": {"values": ["…"], "operator": "or"}}`, `profileHandle` : `{"exactMatch": [...]}`, `publishedAt` : `{"after": "AAAA-MM-JJ", "before": "AAAA-MM-JJ"}`, `platform` ; réponse `{"data": {"results": [...]}, "error": ..., "metadata": {"requestId", "executionTime", "timestamp", "pagination": {"offset", "limit", "totalCount"}}}` ; par résultat (`default`) : `id`, `matchedQueries`, `platform`, `profileHandle`, `platformId`, `publishedAt`, `caption`, `viewsCount`, `interactionsCount`, `media[]` avec `type`, `duration`, `caption`, `onScreenText` (liste de chaînes), `transcript` (chaîne), `tags`.

Champs à REFUSER (jamais écrits ni journalisés) : `profileDisplayName`, `profilePictureUrl`, `thumbnailMediaUrl`, `thumbnailMediaId`, `mentions`, `hashtags`, `coAuthors*`, `audio*`, `media[].tags`, `frames`, `transcriptChunks`, `popularComments`, `location*`, `profileLocation*`, `profileBio`, `profileFollowers*`, `profileFollowing*`, taux d'engagement.

Authentification : aucun schéma dans la spécification ; nom de l'en-tête lu dans `ORIANE_EN_TETE_AUTH` (relevé H01 ; si vide, `Authorization` avec `Bearer`, H). Codes : 402 → `CreditsEpuises` ; expiration (`ORIANE_DELAI_S`) ou autre code → `OrianeInjoignable`. Coût estimé : 15 crédits par page de 100 en `default` (F).

## Ce que S02 fournit (b90aaf6)

Imports : `app.modeles` → `Video`, `Transcription`, `TexteEcran`, `VIDEO_V1` ; `app.libelles` → `contient_libelle_refuse`, `LIBELLES_REFUSES` ; `app.routes` → `erreurs()`, `non_implemente()` ; `app.base` → `ecrire`, `lire`, `consigner`. Fixtures de `tests/conftest.py` : `reponse_oriane_simulee` (forme `metadata` + `data.results[].media[]`), `video_simulee` / `fabriquer_video`, constantes `CHAMPS_TIERS_ORIANE`, `CHAMPS_TIERS_MEDIA_ORIANE`. `onScreenText` (liste) se joint dans `texte_ecran.texte`. `consigner()` refuse `reponse`, les champs inconnus et les clés d'allure secrète (le motif contient `token`) : nommer les champs du journal en conséquence. Mineur de S01 à traiter ici : `securite.py` et `base.py` ne sont pas dans la réserve ; si un blocage apparaît, le noter dans les Échanges plutôt que de les modifier.

Relevé H01 conclu (07/11, un appel réel, F) : en-tête `Authorization: Bearer <clé>` (défauts `ORIANE_EN_TETE_AUTH=Authorization`, `ORIANE_PREFIXE_AUTH` = « Bearer » et une espace, surchargeables) ; succès = **200 ou 206** (206 = page incomplète, `totalCount` > `limit`) ; 401 `{"error": {"operation": "AUTHENTICATION", "code": "UNAUTHORIZED"}}` → `OrianeInjoignable` raison « authentification refusée » ; 400 `{"error": {"operation": "VALIDATION", "context": [{"field", "rule", "message"}]}}` → `OrianeInjoignable` raison « requête refusée : <field> <message> » ; **le filtre `platform` s'écrit `{"includes": ["tiktok"]}`** (pas `exactMatch`) ; `transcript` et `onScreenText` : `includesExactly` ; au niveau `default`, `media[0].transcript` est une chaîne et `media[0].onScreenText` une liste de chaînes, et les champs de tiers listés plus haut sont bien servis : la liste blanche est indispensable. Jamais la clé dans le journal. Le test `reel` (marqueur) fait cet appel avec `limit=1` quand `ORIANE_API_KEY` est posée.

## Fichiers réservés

`02_Service/app/oriane.py`, `app/liste_blanche.py`, `app/routes/videos.py` (remplir la route de S02), `tests/test_oriane.py` ; `tests/conftest.py` : ajout d'une fixture `transport_oriane_simule` (`httpx.MockTransport`) sans retirer les autres. `app/config.py` : ajout des seules clés `ORIANE_PREFIXE_AUTH` (défaut vide) et, si absente, `ORIANE_URL` par défaut `https://connect.oriane.xyz` ; `.env.example` : les deux lignes correspondantes, sans valeur.

## Règle des contrats

Aucun changement de modèle ni de signature de route n'est attendu : les modèles et les routes viennent de S02. Si `test_openapi_egal_au_contrat` échoue malgré tout, relancer `python scripts/exporter_contrats.py` et commiter `contrats/` en le déclarant dans les Échanges ; l'orchestrateur relance l'export à la fusion en cas de conflit.

## État du poste

Venv de S01, fixtures de S01 et S02 (`client`, `video_simulee`, `deux_videos_comparables`, `reponse_oriane_simulee`), aucune clé Oriane : le test `reel` est sauté.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-oriane --limit 1   # completed success
curl -s localhost:8080/v1/videos/<id>   # video.v1 dont transcription.source = "Oriane", transcription.niveau = "default"
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat feat/service-contrats...HEAD` ; run GitHub et nombre de tests ; écarts ; points ouverts (dont la forme exacte du corps de requête envoyé, à relire par P1 avant H01).

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | réalisateur sonnet / medium | Rendu 120183f : `app/oriane.py`, `app/liste_blanche.py`, `app/routes/videos.py`, `app/config.py`, `.env.example`, `tests/test_oriane.py`, `conftest.py` (+923), run 42366568938 vert, 152 tests, test `reel` sauté. Écarts : `tests/test_contrats.py` hors réserve (`ROUTES_IMPLEMENTEES`, commit séparé) ; 501 encore documenté sur la route ; pas de gestionnaire d'enveloppe pour `OrianeInjoignable`, `CreditsEpuises`, `RequeteInvalide` (`erreurs.py` hors réserve → S04) ; `rechercher` asynchrone, rend `ResultatRecherche` (videos, total, ecartees, code, credits_estimes, requete, incomplete) et écrit les vidéos en base ; mode `direct` seulement si config en direct et vidéo écrite en direct. Hypothèse déclarée : `operator: and` racine avec `transcript` et `onScreenText`. |
| 2026-11-07 | orchestrateur | Hypothèse levée par appel réel (limit=1, « retraites ») : `and` racine = intersection (28), `or` racine casse plateforme et date (28 M), forme correcte = racine `and` + sous-requête `or` de deux requêtes nommées `dit` (transcript) et `ecrit` (onScreenText) → 142 (union), `matchedQueries` donne l'origine. Correctif demandé au réalisateur (forme du corps, test de forme, test `reel` lancé une fois avec la clé du poste) ; doublage après le correctif. |
