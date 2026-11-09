---
mandat: F028
titre: Ergonomie des onglets Versions et Fiche de l'espace du récit (actions regroupées, information resserrée)
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: lot 2, ergonomie (veille § 6), hors ADR-0003
depot: EricLtx/tete-de-brut-6a69202a (écrans Lovable)
branche: feat/ecrans-ergonomie-recit
worktree: C:/Users/ericl/dev/tete-de-brut-ecrans-ergonomie (worktree du clone des écrans)
modele: opus
effort: high
relecteur: opus / high (textes et parcours lus par les journalistes)
cree: 2026-11-09
lance_a: 2026-11-09
rendu_a:
go_a:
allers_retours: 0
---

# F028 — Ergonomie des onglets Versions et Fiche

Demande du propriétaire du 09/11, captures à l'appui : « Les boutons sont éloignés, l'information dispersée », enjeu jugé important depuis que la pertinence des données s'est améliorée. Aucun changement de contrat ni d'appel au service.

## Objectif

Dans l'espace du récit, un journaliste compare deux versions, tranche chaque version et enregistre constat et décision sans balayer l'écran : les actions sont groupées près de ce qu'elles touchent, une seule action principale par onglet, les indices de transformation sont lisibles d'un coup d'œil (comptes d'abord, détail replié, texte aligné à côté de chaque version), aucune information n'est perdue.

## Fichiers réservés

Écrans : `src/components/socle/EspaceRecit.tsx`, `src/components/socle/Lecteur.tsx`, `src/components/versions/Versions.tsx`, `src/components/fiche/Fiche.tsx`, nouveaux composants sous `src/components/versions/` et `src/components/fiche/`, `src/test/versions-ergonomie.test.ts`, `src/test/fiche-ergonomie.test.ts` (création). Interdits (F025 en cours) : `__root.tsx`, `styles.css`, `theme.ts`, `ChoixTheme.tsx`, `BarreEtat.tsx`, `AGENTS.md`.

## Critère de fin

Règles d'`AGENTS.md` tenues (attribution à Oriane, aucun classement, aucun libellé refusé, aucune persistance) ; aucune couleur brute (jetons existants seulement) ; tests d'ergonomie qui fixent la nouvelle disposition ; `bun run test` et `bun run build` verts ; branche poussée, jamais `main`.

## Compte rendu (cinq lignes)

sha ; `git diff --stat` ; dernières lignes de `bun run test` et `bun run build` ; écarts ; points ouverts (dont l'alignement des prompts 02 et 03 du kit).

## Échanges

| Date | De | Message |
|---|---|---|
