---
mandat: F010
titre: S06 — Indicateur de vitesse de chaque récit sur deux fenêtres (48 h et 7 jours), méthode affichée, échantillon trop petit refusé
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S06
branche: feat/service-vitesse (part de main après fusion de S05)
worktree: .claude/worktrees/feat-service-vitesse
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a:
rendu_a:
go_a:
allers_retours: 0
---

# F010 — S06, vitesse

Le mandat renvoie à la fiche S06 du plan et au rendu de S05 (`app/recits.py` : `mesures_du_recit(videos, fenetre, calcule_le)` appelle `mesures_de_volume` ; `mesures.echantillon_de(videos)` donne l'échantillon et le drapeau `tronque`). Décision de l'orchestrateur du 07/11 : la vitesse tient en mesures `Mesure` existantes, sans changer le contrat.

## Objectif

Chaque récit du radar porte trois mesures de vitesse calculées sur l'échantillon : vidéos par jour sur les 48 h avant `calcule_le` (÷ 2), vidéos par jour sur les 7 jours (÷ 7), et le rapport des deux ; chacune avec `methode` en clair et sa `fenetre` ; sous 3 vidéos (H) valeur nulle et raison « échantillon trop petit » ; « au moins » dans la méthode quand l'échantillon est tronqué. Aucun mot « tendance », « monte », « viral ».

## Fichiers réservés

`02_Service/app/vitesse.py` (nouveau), `app/recits.py` (une ligne d'appel après `mesures_de_volume`), `tests/test_vitesse.py` (nouveau).

## État du poste

Venv à créer ; fixtures `fabriquer_video` (dates simulées).

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-vitesse --limit 1   # completed success
curl -s localhost:8080/v1/radar   # chaque récit a les mesures de vitesse avec deux fenêtres et une méthode, ou une valeur nulle avec raison
```

Tests exigés : dates simulées connues → valeurs et rapport exacts ; deux vidéos → valeur nulle avec raison ; échantillon tronqué → « au moins » ; aucun libellé refusé.

## Compte rendu attendu (cinq lignes)

sha ; diff ; run et tests ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
