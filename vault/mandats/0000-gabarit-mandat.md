---
mandat: F000
titre: Sujet en une ligne
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S00
branche: feat/<sujet>
worktree: .claude/worktrees/<sujet>
modele: sonnet
effort: medium
relecteur: sonnet / high (config) ; opus / medium si conception
cree: AAAA-MM-JJ
lance_a: AAAA-MM-JJTHH:MMZ
rendu_a:
go_a:
allers_retours: 0
---

# F000 — Sujet en une ligne

Le mandat tient en 250 mots : il renvoie à la fiche `fiche` du plan et au contrat (`02_Service/contrats/`), il ne les recopie pas. Tout ce qui n'y figure pas est hors mandat.

## Objectif

Ce qui doit exister à la fin, en deux phrases. Une seule responsabilité.

## Fichiers réservés

Liste exacte (reprise de la fiche). Tout autre fichier est hors mandat : le signaler, ne pas le toucher. Le réalisateur n'écrit jamais dans ce fichier de mandat.

## État du poste

Réseau, Docker, clé Oriane absente ou présente, version de Python, fixtures disponibles dans `02_Service/tests/conftest.py`.

## Commande de fin et sortie attendue

```bash
04_Pipeline/ci.sh --ref feat/<sujet>      # dernière ligne attendue : « Pipeline locale verte »
# puis la commande du critère de fin de la fiche, avec sa sortie attendue
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat origin/main...HEAD` ; dernière ligne de `ci.sh --ref` ; écarts à la fiche ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
