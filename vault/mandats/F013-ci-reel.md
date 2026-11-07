---
mandat: F013
titre: Job GitHub « reel » à la demande — appel réel Oriane et parcours contre un service lancé
statut: en-doublage
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: hors fiche (vérification avant H07)
branche: pipeline/ci-reel (part de main)
worktree: .claude/worktrees/pipeline-ci-reel
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T13:30Z
rendu_a: 2026-11-07T13:41Z
go_a:
allers_retours: 0
---

# F013 — Job « reel » à la demande

## Objectif

Un workflow `reel.yml`, déclenché par `workflow_dispatch` seulement, lit le secret `ORIANE_API_KEY`, lance `pytest -m reel -s` puis le service en mode direct et rejoue `scripts/verifier_parcours.py` contre lui (S09, sans le modifier). Le workflow `pipeline` existant ne change pas et ne reçoit aucun secret.

## Fichiers réservés

`.github/workflows/reel.yml` (nouveau), un paragraphe dans `01_Docs/04_CICD/pipeline-cicd.md`. Rien d'autre.

## Refuse

Un secret affiché ou écrit en fichier (pas de `set -x`, pas d'`echo`) ; un déclenchement sur `push` ou `pull_request` (crédits Oriane, secrets absents des forks) ; `CLE_DEMO` en dur ; un plafond de crédits relevé (`PLAFOND_CREDITS_JOUR` reste celui du service) ; le secret `ANTHROPIC_API_KEY` (hors mandat, voir F014).

## État du poste

Aucun Python local : la vérification se fait sur GitHub (`workflow_dispatch` sur la branche). Le test `reel` existant est `tests/test_oriane.py::test_appel_reel_une_page_d_un_resultat`.

## Commande de fin et sortie attendue

Le workflow `pipeline` vert sur le sha ; puis un lancement de `reel` sur la branche : ligne `REEL code=200|206 …` dans le journal, `verifier_parcours.py` vert.

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat` ; run `pipeline` et run `reel` ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | orchestrateur (session service) | Lancé sur `pipeline/ci-reel` (worktree `.claude/worktrees/pipeline-ci-reel`), réalisateur sonnet / medium. Le secret `ORIANE_API_KEY` du dépôt GitHub est à poser par le propriétaire (`gh secret set ORIANE_API_KEY`), jamais par un agent ; le run `reel` ne peut être vert qu'après. |
| 2026-11-07 | réalisateur sonnet / medium | Rendu e063d16109af696207eba6ee253c860279999c6b : `.github/workflows/reel.yml` (104 lignes, `workflow_dispatch` seul ; test `reel` avec le secret dans l'environnement de l'étape ; `CLE_DEMO` généré et masqué ; cas minimal « réforme des retraites » sans vidéo dans un dossier temporaire ; service direct, actualisation, échec si `mode` n'est pas `direct`, parcours S09, arrêt par `trap`, ligne `REEL` affichée) et paragraphe dans `pipeline-cicd.md` ; run `pipeline` 42378000436 vert. Écart : type de commit `pipeline` (la garde refuse `ci`). Bloqué : GitHub n'enregistre un `workflow_dispatch` que sur la branche par défaut, le job ne peut être lancé qu'après fusion. Doublage sonnet / high lancé par lecture. |
