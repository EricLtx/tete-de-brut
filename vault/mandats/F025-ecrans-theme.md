---
mandat: F025
titre: S24 — Écrans en clair, sombre ou système (jetons sémantiques, contrastes vérifiés)
statut: en-doublage
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S24
depot: EricLtx/tete-de-brut-6a69202a (écrans Lovable)
branche: feat/ecrans-theme
worktree: C:/Users/ericl/dev/tete-de-brut-ecrans (clone du dépôt des écrans, branche dédiée)
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F025 — S24, thème clair, sombre ou système

Renvoie à la fiche S24 du plan (lot 2). Dépôt des écrans, pas celui du service ; aucun appel au service changé.

## Objectif

Les écrans suivent la préférence du système et offrent un choix à trois états (clair, sombre, système) dans la barre d'état, sans éclair de mauvais thème au chargement, avec des contrastes vérifiés dans les deux thèmes.

## Écart à la fiche, décidé par l'orchestrateur

L'exception de stockage `theme` attend la confirmation du propriétaire (décision ouverte de l'ADR-0003). D'ici là, **aucun stockage du navigateur** : le choix vit en mémoire pour la session et le script du `<head>` applique la préférence du système. `src/lib/theme.ts` isole la lecture et l'écriture du choix derrière deux fonctions, pour qu'un stockage s'ajoute en une ligne après la décision. `AGENTS.md` reçoit une ligne qui le dit.

## Fichiers réservés

Ceux de la fiche S24 (dépôt des écrans). Rien d'autre.

## Critère de fin

Celui de la fiche, hors stockage : préférence du système appliquée avant l'hydratation ; choix à trois états ; aucune couleur brute dans un composant touché ; contrastes de chaque couple texte et fond, statut et surlignage calculés depuis les jetons des deux thèmes (4,5:1 texte, 3:1 composants) ; `bun run test` et `bun run build` verts. Branche poussée, jamais `main` ; historique publié non réécrit.

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernières lignes de `bun run test` et `bun run build` ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
