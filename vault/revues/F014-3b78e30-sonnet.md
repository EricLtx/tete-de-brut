---
mandat: F014
branche: feat/service-modele-langue
commit: 3b78e30b7e7ed0345d6908bee20a591874c8810f
relecteur: sonnet
effort: high
verdict: GO
date: 2026-11-07
---

# Doublage F014 (troisième passage, 3b78e30) — S10, résumé de fiche par Claude

## Verdict

GO. Aucun bloquant, majeur ni nouveau mineur. Le commit ne touche que `app/filtre_sortie.py` et `tests/test_modele_langue.py` (+34/−5) ; `routes/fiches.py`, `modele_langue.py`, `resume.py`, `base.py`, `config.py`, `modeles.py` et `contrats/` sont inchangés depuis 0021d2e. Le test de concurrence corrigé détecte désormais une boucle bloquée.

## Constats

| # | Gravité | Fichier:ligne | Constat | Remède |
|---|---|---|---|---|
| 1 | mineur | `app/filtre_sortie.py:17-62` | Les préfixes ajoutés (`origin`, `biais`, `bidon`) et `contexte`/`premier` refusent aussi des emplois neutres (« d'origine », « le premier tour »). Coût : repli sur le gabarit avec ligne au journal. Aucun mot courant neutre testé n'est touché par les mots entiers `vrai`, `ment`, `menti` (« mentionne », « vraiment », « comment », « commentaire » passent). Reprend le constat 1 du passage précédent, sans l'aggraver. | Mesurer le taux de repli au test réel. |
| 2 | mineur | `app/filtre_sortie.py` | Le filtre reste lexical : toute qualification hors liste passe. Reprend le constat 2 du passage précédent (« montage », « inversé », « dénaturés »). | Enrichir au vu du test réel. |

Constats 3 et 4 du passage précédent (« … » et fil orphelin ; configuration injectée, `thinking`, test `reel`) : inchangés, acceptés.

## Vérifications faites

| Vérification | Commande ou méthode | Résultat |
|---|---|---|
| Run annoncé | `gh run view 42381374549` | success sur la branche |
| Lint | `ruff check .` et `ruff format --check .` | propres, 45 fichiers formatés |
| Tests | `pytest -q -m "not reel"` | 377 passés, 1 sauté, 2 désélectionnés ; sans `test_modele_langue.py` : 302 passés (les 302 antérieurs intacts) |
| Contrats | `scripts/exporter_contrats.py --verifier` | « contrats à jour », sortie 0 |
| Fichiers inchangés depuis 0021d2e | `git diff 0021d2e HEAD` sur `routes/fiches.py`, `modele_langue.py`, `resume.py`, `base.py`, `config.py`, `modeles.py`, `contrats/` | diff vide (0 ligne pour `routes/fiches.py`) |
| Périmètre | `git diff --stat 0021d2e...3b78e30` | 2 fichiers, 34 ajouts, 5 retraits ; commit typé, adresse d'auteur non vide |
| Filtre élargi | 8 textes passés à `_raison_de_refus` | refusés : « le propos est vrai », « il ment », « version d'origine », « le sens est modifié » ; acceptés : « mentionne un chiffre, comment il change, vraiment », « la reprise ajoute dix mots », « un commentaire est ajouté dans la légende », « la parole 1 retire des mots » |
| Test de concurrence corrigé | trois exécutions ; mutation hors dépôt remplaçant `run_in_threadpool` par un appel direct (boucle bloquée) | vert trois fois (1,6 s) ; avec la boucle bloquée : échec `1.54 < 0.8` faux, donc le test détecte la régression (avant correction, il ne la voyait pas) |
| Fuite de clé | code d'appel et de journal inchangés depuis le passage précédent (28 cas rejoués alors, clé absente partout) | pas de changement de surface ; non rejoué |
| Test `reel` | non lancé (consigne) | non fait |

## Mandats de suite

Aucun obligatoire. Lancer le test `reel` par une personne avant la démonstration.
