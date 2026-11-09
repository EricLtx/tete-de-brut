---
mandat: F024
branche: feat/service-banc-evaluation
commit: a3d1efe043e5b73cb9b9a7e14136bc974ee70508
relecteur: sonnet
effort: high
verdict: GO
date: 2026-11-09
---

# Doublage F024 — S22, banc d'évaluation rejouable sans réseau

## Verdict

GO. Critère de fin tenu : rappel@k et nDCG@k exacts (recalculés à la main), jeu mal formé refusé, `evaluation/donnees/` ignoré par Git (mutation détectée), jeu simulé de trois questions rejoué contre `TestClient` avec un rapport lisible, sans réseau. Aucun bloquant, aucun majeur ; trois constats mineurs.

## Constats

| # | Gravité | Constat | Fichier:ligne | Preuve |
|---|---|---|---|---|
| 1 | mineur | Une panne du service en cours de jeu (`httpx.HTTPError`) fait perdre les résultats déjà obtenus : aucun rapport partiel n'est écrit, code 1. Sur 30 questions réelles à crédits comptés, c'est dommage. | `02_Service/scripts/evaluer.py` `main` (bloc `except httpx.HTTPError`) | `evaluer()` rend une liste d'un bloc ; l'exception remonte avant `ecrire_rapports` |
| 2 | mineur | Le rapport JSON écrit les identifiants de vidéos rendues (`rendues`). Pas de texte ni de compte, et le dossier est hors Git, mais la phrase « le rapport nomme les questions par leur identifiant » ne couvre pas ce champ. | `02_Service/scripts/evaluer.py` `ResultatQuestion` / `rapport_json` | lecture du code ; JSON du test : identifiants `cnt_…` seulement |
| 3 | mineur | Le test charge le script par `importlib` en posant `sys.modules["evaluer"]` à l'import du module de test (effet de bord global, sans nettoyage). | `02_Service/tests/test_evaluation.py` `_charger_script` | lecture du code ; sans effet observé sur les 687 tests |

Note hors constat : la règle 5 du CLAUDE.md (alignement du plan à chaque étape terminée) n'est pas portée par ce mandat, qui ne réserve pas le plan ; l'alignement du journal du plan relève de l'orchestrateur à la fusion.

## Vérifications faites

| Vérification | Commande ou méthode | Résultat |
|---|---|---|
| Périmètre | `git diff --stat origin/main...a3d1efe` | 8 fichiers (7 de la fiche S22 + ligne du registre) ; rien dans `app/`, `contrats/`, `conftest.py`, gardes ou config du harnais |
| Commits | `git log --oneline origin/main..a3d1efe` | `feat(evaluation): …` + fusion de `origin/main` ; messages typés |
| ruff | `ruff check .` ; `ruff format --check .` (Python du checkout principal, depuis le worktree ; `app` et `evaluation` importés depuis le worktree) | « All checks passed » ; « 57 files already formatted » |
| pytest | `pytest -q -m "not reel"` | 687 passés, 1 sauté, 5 désélectionnés |
| Run GitHub | `gh run list --branch feat/service-banc-evaluation` | `pipeline` completed success, `headSha` = a3d1efe043e5b73cb9b9a7e14136bc974ee70508 |
| Métriques à la main | rendues [a,x,b,y,c], pertinentes [a,b,c,d], k=3 : rappel 2/4 = 0,5 ; DCG = 1 + 1/log2(4) = 1,5 ; IDCG = 1 + 1/log2(3) + 1/log2(4) ; nDCG = 0,70392 | code et calcul manuel identiques (0,5 et 0,7039180890) |
| k plus grand que la liste | k=100 sur la même liste | rappel 0,75 et nDCG 0,73659 = calcul manuel (IDCG borné à min(k, \|pertinents\|)) ; pas d'erreur |
| Pertinents vides | `rappel_a_k(..., [], 3)` ; `ndcg_a_k(..., [], 3)` | `ValueError` « indéfini » (refus explicite, testé) ; k < 1, bool et non entier refusés |
| Jeu mal formé | 18 cas paramétrés + JSON cassé, fichier absent, `--k 0` | tous refusés, code 2 ; test de concordance schéma / validateur écrit à la main |
| Git ignore | `git check-ignore -v evaluation/donnees/jeu-or.json` | ignoré par `02_Service/evaluation/.gitignore:2` ; `metriques.py` et le schéma restent suivis ; `git ls-files evaluation` ne liste aucune donnée |
| Réseau | lecture de `test_evaluation.py` | `TestClient` + `transport_oriane_simule` / `construire_config` / `cas_simule` de `conftest.py`, rien redéfini ; bras refusés vérifiés sans aucun appel |
| Rapport lisible | test « trois questions » rejoué avec `-s` et `--basetemp` hors dépôt | rapport en comptes (« 1 sur 3 », « 3 sur 5 », crédits 45), nDCG q2 = 0,39 (= 1/log2(3) / (1 + 1/log2(3))), mention « pas une inférence statistique » ; `.txt` et `.json` écrits |
| CLI | `scripts/evaluer.py --bras multi` ; `--adresse http://127.0.0.1:1` | code 2 avec « disponible à partir de S29 » ; code 1 « service injoignable (ConnectError) », aucun fichier écrit |
| Données réelles | lecture du diff, recherche de courriels et clés | textes tous simulés (« propos simulé », identifiants `cnt_SIMULE…`) ; aucun compte, aucune question réelle ; aucune adresse de courriel |
| Mutation 1 | nDCG avec `log2(rang)` au lieu de `log2(rang + 1)` | 5 tests échouent (dont `test_ndcg_sur_des_listes_connues`) ; restauré |
| Mutation 2 | `evaluation/.gitignore` remplacé par un commentaire | `test_le_dossier_de_donnees_du_banc_est_ignore_par_git` échoue ; restauré |
| Worktree après relecture | `git status --short` après `git checkout -- .` | propre |
| Registre | diff de `registre-documentation.md` | une ligne pour `evaluation/README.md` |
| markdownlint | `npx -y markdownlint-cli2` sur le README et le registre | 0 problème |
| Jetons | lecture de `evaluer.py` | `jetons` reste `None`, rapport « non mesurés » ; cohérent avec l'absence d'usage exposé par le bras `unique` ; part de synthèse rattachée renvoyée à S32 (conforme à la fiche : « dès S32 ») |

## Mandats de suite

Aucun obligatoire. Option : rapport partiel écrit avant de sortir en code 1 (constat 1), à grouper avec S29 quand les bras `multi` et `boucle` seront branchés.
