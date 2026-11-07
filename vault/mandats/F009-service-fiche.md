---
mandat: F009
titre: S08 — Fiche de vérification par gabarit déterministe, gestes du journaliste, décision, export HTML verrouillé
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S08
branche: feat/service-fiche (part de main après fusion de S07)
worktree: .claude/worktrees/feat-service-fiche
modele: opus
effort: medium
relecteur: sonnet / high (config ; la garde n'accepte que ce relecteur)
cree: 2026-11-07
lance_a:
rendu_a:
go_a:
allers_retours: 0
---

# F009 — S08, fiche de vérification

Le mandat renvoie à la fiche S08 du plan, aux modèles `fiche.v1` et `decision.v1` de S02 (`Fiche`, `VersionFiche`, `Resume`, `GesteFiche`, `Decision`, `Segment`, `DemandeFiche`, `ModificationFiche`, `VersionTranchee`, `DemandeDecision`, constantes `FICHE_V1`, `DECISION_V1`, `METHODE_GABARIT_V1`, `LIMITE_TRANSCRIPTIONS`) et au rendu de S07 (`ecart.v1` : opérations avec positions dès 0 dans les listes `mots.v1`, un bloc contigu = une opération, trois listes : parole, légende, texte à l'écran). Il ne les recopie pas.

## Objectif

Une fiche se construit depuis une comparaison par un gabarit déterministe (phrases fixes en segments `libelle`, extraits en segments `citation`, méthode « gabarit v1 » affichée), reçoit les gestes du journaliste (versions tranchées « confirmée » ou « écartée » avec note, constat écrit par lui) et une décision (`a_verifier`, `ne_pas_amplifier`, `pret_a_traiter`), et ne s'exporte en page HTML lisible qu'une fois décision, versions tranchées et constat présents : sinon 409 `decision_manquante`, `version_non_tranchee` ou `constat_manquant` dans l'enveloppe, même par appel direct.

## Règles de confiance (testées)

Aucun libellé refusé (`contient_libelle_refuse`) dans un segment `libelle` du gabarit ; aucun constat pré-rempli par la machine (constat vide à la création) ; aucune transcription intégrale dans l'export (extraits de 40 mots au plus, H) ; tout élément marqué « selon Oriane » (jamais « preuve ») ; les textes des vidéos sont échappés dans l'export HTML (jamais interprétés) ; `mode` et date sur la fiche et l'export ; `PATCH` et `POST` exigent `X-Cle-Demo` quand `CLE_DEMO` est posée.

## Fichiers réservés

`02_Service/app/resume.py` (`resumer(comparaison)` : point d'entrée unique que S10 pourra étendre), `app/fiche.py`, `app/export.py`, `app/routes/fiches.py` (remplir les cinq routes), `tests/test_fiche.py`, `tests/conftest.py` (ajout d'une fixture `comparaison_simulee`), `tests/test_contrats.py` (constante `ROUTES_IMPLEMENTEES` : y ajouter les cinq routes de fiche ; `erreurs(501)` retiré de ces routes et `contrats/` réexporté en le déclarant). Rien dans `app/modeles.py` : si un champ manque, le dire dans les Échanges plutôt que de changer le contrat.

## État du poste

Venv à créer dans le worktree ; fixtures `deux_videos_comparables` (S02), route `POST /v1/comparaisons` (S07) pour produire une comparaison en test.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-fiche --limit 1   # completed success
curl -s -X POST localhost:8080/v1/fiches -H 'Content-Type: application/json' -d '{"comparaison": "<id>"}'   # fiche.v1, constat vide, résumé « gabarit v1 »
curl -s localhost:8080/v1/fiches/<id>/export   # 409 decision_manquante ; après PATCH (versions, constat) et POST decision : 200 text/html
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; run et tests ; écarts ; points ouverts pour S09 et S10 (parcours complet, signature de `resumer`).

## Échanges

| Date | De | Message |
|---|---|---|
