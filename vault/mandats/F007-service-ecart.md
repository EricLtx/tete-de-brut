---
mandat: F007
titre: S07 — Écart au mot entre deux vidéos sur la normalisation mots.v1, POST /v1/comparaisons idempotent et GET /v1/comparaisons/{id}
statut: fusionne
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S07
branche: feat/service-ecart (part de feat/service-contrats à 407a5c7 ; fusion après S02)
worktree: .claude/worktrees/feat-service-ecart
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T10:52Z
rendu_a: 2026-11-07T11:01Z
go_a: 2026-11-07T11:18Z
allers_retours: 0
---

# F007 — S07, écart au mot

Le mandat renvoie à la fiche S07 du plan, au complément de contrat e (idempotence) et au modèle `ecart.v1` de S02. Il ne les recopie pas.

## Objectif

Deux vidéos présentes en base sont comparées mot à mot (distance d'édition par programmation dynamique en Python standard sur `mots.v1`, opérations retiré, ajouté, remplacé avec positions), ainsi que leurs légendes et textes à l'écran, sans aucun champ de qualification ; l'identifiant de la comparaison dérive des deux identifiants de vidéo (même couple, même ressource, 200 à la seconde demande) ; heure dans la vidéo « non fournie au niveau default ».

## Ce que S02 fournit (b90aaf6)

Imports : `app.modeles` → `Ecart`, `Operation`, `AttributionTranscription`, `TranscriptionsComparees`, `HeureDansLaVideo`, `DemandeComparaison`, `ECART_V1`, `LIBELLE_HEURE_NON_FOURNIE` ; `app.mots` → `normaliser`, `NORMALISATION_MOTS_V1` (ponctuation supprimée, apostrophe et trait d'union devenant une espace) ; `app.base` → `lire`, `ecrire`. Contrainte : une `Operation` vérifie que ses mots correspondent à son type (`retire` sans mots ajoutés, etc.). Fixture `deux_videos_comparables` : la reprise retire « si l'État paie » (quatre mots). La route de S02 rend 200 à chaque `POST` : conserver 200 et l'idempotence (identifiant dérivé des deux identifiants, ordre source puis reprise).

## Fichiers réservés

`02_Service/app/ecart.py`, `app/routes/comparaisons.py` (remplir les deux routes de S02), `tests/test_ecart.py`.

## Règle des contrats

Aucun changement de modèle ni de signature de route n'est attendu : les modèles et les routes viennent de S02. Si `test_openapi_egal_au_contrat` échoue malgré tout, relancer `python scripts/exporter_contrats.py` et commiter `contrats/` en le déclarant dans les Échanges ; l'orchestrateur relance l'export à la fusion en cas de conflit.

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
| 2026-11-07 | réalisateur sonnet / medium | Rendu 71d4c17 : `app/ecart.py`, `app/routes/comparaisons.py`, `tests/test_ecart.py` (+330), run GitHub 42366312318 vert, 122 tests. Écarts : `tests/test_contrats.py` modifié hors réserve (ensemble `ROUTES_IMPLEMENTEES` qui exclut les routes remplies du test 501 ; S03 et S05 toucheront le même endroit, conflit trivial à unir à la fusion) ; validateur de schéma local dans le test (jsonschema hors pile) ; identifiant `cmp-` + sha256[source, reprise](:12), document de type `ecart`, vidéos lues sous le type `video`. Pour S08 : positions dès 0 dans les listes `mots.v1`, un bloc contigu = une opération, trois listes (parole, légende, texte à l'écran) et la ligne « heure dans la vidéo : non fournie ». |
| 2026-11-07 | relecteur sonnet / high | GO sur 71d4c17 : 0 bloquant, 0 majeur, 3 mineurs (mémoire O(n·m) mesurée : 600×600 en 0,05 s et 10 Mo, 3 000×3 000 en 1,4 s et 350 Mo, plafond ou mémoire linéaire après la démonstration, calcul bloquant en `async def` ; `ROUTES_IMPLEMENTEES` hors réserve acceptable ; écart figé à la première demande, conforme). Service rejoué sur 8085, 122 tests, export vérifié. Fusionné sur `main`. |
