---
mandat: F022
titre: S19 — Compteurs de vitesse ancrés sur la vidéo la plus récente retrouvée (plus de « Non mesuré » quand l'index date de quelques semaines)
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S19
branche: feat/service-vitesse-ancree (part de main)
worktree: .claude/worktrees/feat-service-vitesse-ancree
modele: sonnet
effort: medium
relecteur: sonnet / medium (doublage allégé sur demande du propriétaire du 07/11, 17 h 50)
cree: 2026-11-07
lance_a: 2026-11-07T17:05Z
rendu_a:
go_a:
allers_retours: 0
---

# F022 — S19, compteurs de vitesse ancrés sur les vidéos

## Constat du propriétaire (07/11, 17 h 50, sur le service réel)

Sur chaque récit, les trois compteurs de vitesse (S06) affichent « Non mesuré : échantillon trop petit (0 vidéo(s) dans la fenêtre) ». Cause : `app/vitesse.py` (`mesures_de_vitesse(videos, calcule_le)`) compte les vidéos publiées dans les 48 heures et les 7 jours **avant le calcul** (07/11 à 17 h 02), alors que l'index Oriane rend des vidéos publiées entre le 1er et le 23 octobre 2026. Les fenêtres sont donc toujours vides et le journaliste voit « aucun calcul ». Les autres mesures (vidéos, comptes, vues) se calculent bien.

Le mandat renvoie à `app/vitesse.py` (`_mesure_par_jour`, `mesures_de_vitesse`, `RAISON_TROP_PETIT`, seuil de trois vidéos), `app/modeles.py` (`Mesure` : `valeur`, `methode`, `fenetre`, `raison`), `app/recits.py` (appelant, **réservé par F020 en parallèle : ne pas y toucher**) et `tests/test_vitesse.py` ; il ne les recopie pas.

## Objectif

1. **Ancrage.** La référence des deux fenêtres devient la date de publication de la vidéo **la plus récente** du récit (`max(v.publie_le)`), plafonnée à `calcule_le` si elle lui est postérieure ; sans vidéo, la référence reste `calcule_le`. Fenêtre courte : 48 heures avant la référence ; fenêtre longue : 7 jours avant la référence ; `fenetre` de chaque `Mesure` porte ces bornes. Le rapport (48 h / 7 jours) garde sa règle (les deux fenêtres calculables).
2. **Méthode dite.** Le texte `methode` dit la référence : « nombre de vidéos publiées dans les 48 heures avant la vidéo la plus récente retrouvée (le 23/10/2026 à 10 h 54), divisé par 2 jours ; sous 3 vidéos, aucune valeur » (même forme pour 7 jours ; la date suit le format déjà utilisé dans le service). Sans vidéo : « avant le calcul ».
3. **Seuil.** Inchangé : sous trois vidéos dans la fenêtre, `valeur` null et `raison` « échantillon trop petit (n vidéo(s) dans la fenêtre) ».
4. **Contrats.** Aucun champ nouveau ; si une description de `recit.v1` ou `api.v1` dit « avant le calcul », la corriger et réexporter (`python scripts/exporter_contrats.py` puis `--verifier`).

## Fichiers réservés

`app/vitesse.py`, `tests/test_vitesse.py`, `contrats/recit.v1.schema.json` et `contrats/api.v1.json` (descriptions seulement, réexport), `03_Ecrans/exemples/recit.json` et `radar.json` seulement si le test du kit l'exige. Rien dans `app/recits.py`, `app/recherche.py`, `app/modeles.py` (F020 et F021 en parallèle).

## Règles de confiance (testées)

La méthode dit la référence et les bornes ; une mesure sans valeur dit pourquoi ; aucune valeur inventée hors des vidéos consultées ; `mode` inchangé.

## État du poste

Python 3.12 dans `C:\Users\User\AppData\Local\Programs\Python\Python312` (hors PATH), venv `C:\Users\User\AppData\Local\Temp\claude\venv-f011`. Aucun appel réseau.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-vitesse-ancree --limit 1   # completed success
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; tests ; écarts ; exemple de mesure rendue sur un récit dont les vidéos datent d'octobre (valeur, méthode, fenêtre).

## Échanges

| Date | De | Message |
|---|---|---|
