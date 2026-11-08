---
mandat: F023
titre: S20 — Correctifs d'après les doublages (plafond sous verrou, purge ciblée, cache, suppression atomique, sortie du script de parcours)
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S20
branche: fix/service-correctifs-doublages (part de main après fusion de F020)
worktree: .claude/worktrees/fix-service-correctifs-doublages
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-09
lance_a:
rendu_a:
go_a:
allers_retours: 0
---

# F023 — S20, correctifs d'après les doublages

Renvoie à la fiche S20 du plan et aux constats cités ci-dessous ; aucun changement de contrat (`02_Service/contrats/` intouché).

## Objectif

Fermer six constats mineurs sans changer le comportement visible : F016 n° 5 et 6, F018 n° 1 et 2, F019 n° 1 et 3, F021 n° 3 (rapports dans `vault/revues/`), et retirer les comptes des vidéos de la sortie de `scripts/verifier_parcours.py` (journal public du run `reel`, plan, ligne du 07/11 sur F013).

## Fichiers réservés

Ceux de la fiche S20 ; tests dans `tests/test_<module>.py` existants, réponses Oriane simulées de `tests/conftest.py` réutilisées.

## Critère de fin

Trois recherches simultanées sous un plafond de 20 crédits : une seule appelle Oriane (test) ; une recherche et une actualisation simultanées idem ; un document `cas` autre que `recherche-*` survit à la bascule ; une suppression interrompue ne laisse rien à moitié ; la suppression est testée en mode direct ; la sortie du script ne contient aucun compte.

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"
gh run list --branch fix/service-correctifs-doublages --limit 1   # completed success
```

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernière ligne de pytest ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-09 | orchestrateur | Ajout au périmètre : les lignes `REEL` imprimées par les tests réels (`tests/test_recherche.py`, liens collés) affichent l'URL complète d'une vidéo, compte compris, dans le journal public du run `reel` 42534842980 ; n'imprimer que la plateforme et l'identifiant de la vidéo. Même critère : aucune sortie publique ne contient un compte. |
