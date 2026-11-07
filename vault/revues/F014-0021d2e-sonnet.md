---
mandat: F014
branche: feat/service-modele-langue
commit: 0021d2e5e2da5c4338a73d58a6dc3709324b9ae6
relecteur: sonnet
effort: high
verdict: GO
date: 2026-11-07
---

# Doublage F014 (second passage, correctif 0021d2e) — S10, résumé de fiche par Claude

## Verdict

GO. Aucun bloquant ni majeur. Les deux majeurs et les cinq mineurs du passage sur 724e646 sont corrigés ou acceptés : l'appel au modèle ne bloque plus la boucle (un `GET /sante` concurrent d'un appel de 2 s répond en 3 ms de service, contre 2,04 s avant), le plafond global de 10 s tient (fiche en gabarit à 10,04 s, ligne au journal), plus aucune réponse déformée ne donne 500, et la clé ne fuit toujours ni au journal, ni dans une exception, ni dans la fiche. Quatre mineurs résiduels, sans effet sur la sécurité.

## Constats

| # | Gravité | Fichier:ligne | Constat | Remède |
|---|---|---|---|---|
| 1 | mineur | `app/filtre_sortie.py:16-38` | Faux positifs probables dans le domaine : le préfixe `premier` refuse « le premier tour » ; `contexte` refuse tout « contexte ». Coût limité au repli sur le gabarit (ligne au journal), mais le taux de repli sera mesurable sur des extraits électoraux. | Surveiller le taux de repli au test réel ; au besoin, passer `premier` en mot entier avec la liste des accords. |
| 2 | mineur | `app/filtre_sortie.py:16-38` | Filtre lexical : des qualifications hors liste passent (« montage », « inversé », « erronée », « dénaturés », « hoax »). Inhérent à la méthode ; la consigne les interdit en amont, le champ `decision` reste humain, le résumé est marqué « à relire ». | Aucun correctif demandé ; enrichir la liste au vu du test réel. |
| 3 | mineur | `app/resume.py:146-150`, `app/modele_langue.py:158-165` | Le « … » n'est plus une fin de phrase (choix voulu, pour ne pas compter les extraits coupés) : un texte séparé uniquement par des « … » échappe au plafond de quatre phrases. Et sur expiration, le fil de l'appel reste actif jusqu'aux délais httpx par phase (un fil orphelin par expiration, mesuré : `modele_0` encore présent). Borné, sans fuite d'information. | Mandat ultérieur éventuel : compter les « … » entre mots comme séparateur ; annuler la requête à l'expiration. |
| 4 | mineur | `app/resume.py` (`resumer`) | Inchangé et accepté : `resumer` lit l'environnement et ignore la `Configuration` injectée ; `thinking` non envoyé (non fait, déclaré). Le test `reel` reste à lancer par une personne : l'acceptation de `output_config.effort` et de `claude-sonnet-5-5` par l'API réelle n'est pas vérifiée. | Lancer le test `reel` avant la démonstration. |

Constats du passage précédent : 1 (appel bloquant) corrigé ; 2 (`base.py` hors réserve) accepté par l'orchestrateur, `base.py` inchangé dans ce correctif ; 3 (`TypeError`, `InvalidURL`) corrigé ; 4 (décisions sans accents, identifiants) corrigé ; 5 (sauts de ligne, balises) corrigé ; 6 accepté.

## Vérifications faites

| Vérification | Commande ou méthode | Résultat |
|---|---|---|
| Run annoncé | `gh run view 42380635333` | success sur la branche |
| Lint | `ruff check .` et `ruff format --check .` | propres, 45 fichiers formatés |
| Tests | `pytest -q -m "not reel"` | 363 passés, 1 sauté, 2 désélectionnés ; sans `test_modele_langue.py` : 302 passés (les 302 antérieurs intacts) |
| Contrats | `scripts/exporter_contrats.py --verifier` | « contrats à jour », sortie 0 ; `modeles.py`, `contrats/`, `base.py` et `config.py` inchangés depuis 724e646 |
| Périmètre | `git diff --stat 724e646...0021d2e` | `filtre_sortie.py` (nouveau), `modele_langue.py`, `resume.py`, `routes/fiches.py`, tests et mandat (ligne d'Échanges). `routes/fiches.py` et `filtre_sortie.py` hors réserve initiale, déclarés par le correctif et exigés par les constats ; aucun fichier de garde, de CI ou de config. Commit typé, adresse d'auteur non vide |
| Concurrence | `ASGITransport`, création de fiche avec transport simulé de 2 s, `GET /sante` concurrent | création 201, `/sante` répond après 0,317 s au total pour 0,3 s d'attente (2,04 s avant le correctif) |
| Dépassement de 10 s | même montage, transport simulé de 12 s | fiche 201 en gabarit à 10,04 s ; journal `modèle injoignable : expiration après 10 s`, durée 10 009 ms ; `/sante` concurrent en 3 ms |
| Fuite de clé | 28 cas rejoués (exception httpx dont le message porte la clé et `x-api-key`, expiration, 307, 429, 529, réponses déformées) ; journal, logs capturés, fiche relus | clé absente partout, y compris au dépassement de délai ; exceptions remplacées par une phrase fixe |
| Mutations rejouées (une ligne au journal chacune, gabarit servi) | script hors dépôt | « Faux », « FAUSSE », « deformee », « manipulée » : libellé ; cinq phrases : refus ; « NE PAS AMPLIFIER », « prêt à traiter » : décision ; 429, 529, expiration, `ConnectError`, `InvalidURL`, `DecodingError` : injoignable ; JSON mal formé, `content` entier, liste JSON : réponse illisible ; réponse vide, `content` nul ou chaîne : réponse vide ; six puces : refus de mise en forme ; bloc `thinking` en premier avec « faux » : seul le bloc `text` est servi |
| Filtre de sortie | 19 textes passés à `_raison_de_refus` après assainissement | refusés : `ne_pas_amplifier`, « n'amplifiez pas », `a_verifier`, « prête à traiter », « mensongère », « truquée », « trompeuse », « désinformation », « faussés », « déforme », « premier tour » (faux positif, constat 1) ; acceptés : trois textes neutres et la phrase de repli de la consigne ; passent à tort : constat 2 |
| Corps envoyé | corps réel capturé | inchangé : cinq extraits `citation` entre `<extraits>`, aucun champ de tiers |
| Lint des `.md` | seul le mandat touché (une ligne de tableau) | non rejoué (`check-docs.sh` hors périmètre de ce passage) |
| Test `reel` | non lancé (consigne) | non fait |

## Mandats de suite

Aucun obligatoire. Suggestions : lancer le test `reel` par une personne avant la démonstration (constat 4) ; mesurer le taux de repli sur les extraits réels et ajuster le préfixe `premier` (constat 1).
