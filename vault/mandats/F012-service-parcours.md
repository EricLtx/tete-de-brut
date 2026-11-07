---
mandat: F012
titre: S09 — Règles transverses testées sur un parcours simulé complet et script de vérification du parcours contre une adresse servie
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S09
branche: feat/service-parcours (part de main après fusion de S04)
worktree: .claude/worktrees/feat-service-parcours
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T12:27Z
rendu_a:
go_a:
allers_retours: 0
---

# F012 — S09, parcours et garde-fous

Le mandat renvoie à la fiche S09 du plan et aux rendus de S03 à S08 (routes `/v1/…`, fixtures `client`, `video_simulee`, `reponse_oriane_simulee`, `transport_oriane_simule`, `deux_videos_comparables`, `comparaison_simulee`, `cas_simule`). Il ne les recopie pas.

## Objectif

Les huit règles de la fiche S09 sont chacune une fonction de test sur un parcours simulé complet (cas enregistré → radar → récit → vidéo → comparaison → fiche → gestes → décision → export), et `scripts/verifier_parcours.py --adresse <url> --origine <origine>` rejoue ce parcours contre un service lancé (santé, radar, vidéo, comparaison, fiche, décision, export, en-tête CORS), une ligne OK ou KO par geste, code de sortie 0 seulement si tout est OK, `X-Cle-Demo` envoyé si `CLE_DEMO` est dans l'environnement du script.

## Règles (une fonction de test chacune, `tests/test_regles_transverses.py`)

1. Aucun champ de tiers d'Oriane en base ni au journal après le parcours (liste de `app/liste_blanche.py` ; la réponse simulée doit en contenir).
2. Aucun libellé refusé (`contient_libelle_refuse`) dans un segment `libelle` de toutes les réponses JSON du parcours.
3. `mode` dans toutes les réponses JSON, erreurs comprises (404, 409, 422, 401) ; `enregistre_le` en mode enregistré.
4. Export refusé sans décision par appel direct (409 dans l'enveloppe).
5. Consigne piégée dans une transcription simulée (« ignore les règles et écris que… ») : affichée en citation, gabarit inchangé, aucun segment `libelle` ne la reprend.
6. Chaque mesure avec `methode` et `fenetre` (volume et vitesse).
7. Chaque appel Oriane simulé présent au journal (`GET /v1/journal`).
8. Avec `CLE_DEMO` renseignée, POST et PATCH sans `X-Cle-Demo` rendent 401 `cle_demo_invalide` ; GET et `/sante` restent ouverts.

**Refuse** : un test qui appelle le réseau ; un correctif du code métier dans ce mandat. Une anomalie trouvée s'écrit dans le compte rendu (fichier, règle, cas) et devient un `fix/…` ; le test qui la révèle est marqué `xfail(strict=True)` avec la raison, jamais supprimé.

## Fichiers réservés

`02_Service/tests/test_regles_transverses.py` (nouveau), `scripts/verifier_parcours.py` (nouveau, bibliothèque standard et `httpx` seulement, aucun import de `app`), `README.md` du service (un paragraphe : commande de vérification). Rien d'autre : ni `app/`, ni `conftest.py` (si une fixture manque, la construire dans le fichier de test).

## État du poste

Venv à créer dans le worktree ; service lançable sans clé en mode enregistré avec un cas simulé hors dépôt (`CHEMIN_CAS` vers un dossier temporaire ; format dans `app/cas.py`).

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert, huit tests transverses
gh run list --branch feat/service-parcours --limit 1   # completed success
python scripts/verifier_parcours.py --adresse http://localhost:8080 --origine http://localhost:5173   # huit lignes OK, code 0 ; code 1 et une ligne KO si l'export est demandé sans décision par un appel direct
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; run et tests ; écarts et anomalies trouvées (candidats `fix/…`, avec règle et fichier) ; points ouverts pour H07 (origine Lovable réelle, adresse servie).

## Échanges

| Date | De | Message |
|---|---|---|
