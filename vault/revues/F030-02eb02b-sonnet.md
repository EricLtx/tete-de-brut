---
mandat: F030
branche: fix/service-base-wal
commit: 02eb02b6424e2c62af5d476367da0ed4e6b05c86
relecteur: sonnet
effort: high
verdict: GO
date: 2026-11-09
---

# Doublage — F030 (sonnet, indépendant)

## Verdict

GO. Critère de fin tenu et rejoué : lecture pendant une écriture ouverte, journal en WAL, schéma préparé une fois, fichiers WAL ignorés par Git. Les deux mutations demandées font échouer un test. ruff et pytest verts (deux passages), run GitHub vert sur ce sha exact. Aucun bloquant ni majeur ; quatre mineurs.

## Constats

| # | Gravité | Constat | Fichier:ligne | Preuve |
|---|---|---|---|---|
| 1 | mineur | `lister_avec_identifiants` du module (lecture pure) reste en `BEGIN IMMEDIATE` ; ses seuls usages réels passent par `Transaction` avant écriture, donc voulu. | `02_Service/app/base.py:221-224` | grep : aucun appel du module dans `app/` |
| 2 | mineur | Le cache se fie à `cible.exists()` et à un `Path` non résolu : un fichier recréé vide par un tiers ne serait pas re-préparé ; chemin relatif et absolu = une préparation de plus (idempotente). Aucun chemin du service ne produit ces cas. | `02_Service/app/base.py:~109-116` | lecture du code |
| 3 | mineur | Aucun test ne force la branche `mode != "wal"` (message d'erreur) ; elle est couverte indirectement par `test_journal_en_wal`. | `02_Service/app/base.py:101-103` | lecture du diff |
| 4 | mineur | `test_fichiers_de_base_ignores_par_git` échouerait (code 128) au lieu d'être sauté hors dépôt Git alors que `git` est installé. Sans effet en CI et sur les postes actuels. | `02_Service/tests/test_base.py:119-130` | lecture du code |

## Vérifications faites

| Vérification | Commande ou méthode | Résultat |
|---|---|---|
| Périmètre | `git diff --stat origin/main...02eb02b` | 3 fichiers (`.gitignore`, `02_Service/app/base.py`, `02_Service/tests/test_base.py`), tous dans la réserve (élargie à `.gitignore`) ; `main.py`, gardes, config, workflow non touchés |
| Commits | `git log --oneline origin/main..02eb02b` | 2 commits typés `fix(base)` et 2 fusions de `origin/main` |
| Ruff | `ruff check .` ; `ruff format --check .` (depuis `<worktree>/02_Service`, venv principal) | All checks passed ; 58 files already formatted |
| Tests, passage 1 | `pytest -q -m "not reel"` | 706 passed, 1 skipped, 5 deselected, 38,6 s |
| Tests, passage 2 | idem | 706 passed, 1 skipped, 5 deselected, 36,6 s |
| Run GitHub | `gh run list --branch fix/service-base-wal --limit 3 --json ...` | `pipeline` completed success, headSha 02eb02b6424e2c62af5d476367da0ed4e6b05c86 |
| Critère de fin : lecture pendant écriture | `test_lecture_pendant_une_ecriture_ouverte` (fil écrivain, lectures `lire`/`lister`/`lire_journal`, instantané sans l'écriture non validée) | vert |
| Critère de fin : WAL | `test_journal_en_wal` ; `_creer_schema` lève si le mode obtenu n'est pas `wal` | vert |
| Critère de fin : schéma non recréé | `test_schema_cree_une_seule_fois` (espion sur `_creer_schema`, 5 tours de 5 opérations) ; `test_base_supprimee_est_recreee` | verts |
| Critère de fin : fichiers WAL ignorés | `test_fichiers_de_base_ignores_par_git` x4 (`sqlite`, `-wal`, `-shm`, `-journal`) | verts |
| Sémantique inchangée | lecture du diff : `transaction()`, `purger`, `consigner`, `ecrire`, `supprimer` gardent `ecriture=True` par défaut donc `BEGIN IMMEDIATE` ; seuls `lire`, `lister`, `lire_journal` passent en `BEGIN` ; `test_ecriture_reste_exclusive` et `test_transaction_annulee_en_cas_d_erreur` verts | conforme |
| busy_timeout | `PRAGMA busy_timeout = 5000` posé dans `_ouvrir`, utilisé aussi pour la création du schéma | conforme |
| Cache de préparation | sonde : 8 fils x 20 écritures/lectures/consignations sur base neuve dans un dossier absent | 0 erreur, 160 documents, 160 lignes de journal ; double contrôle sous verrou, ajout au cache après création ; base supprimée recréée (test) |
| Mutation 1 : `BEGIN IMMEDIATE` remis dans `lire` | `sed` sur `base.py` | `test_lecture_pendant_une_ecriture_ouverte` échoue (1 failed, 9 passed) |
| Mutation 2 : `*.sqlite-wal` retiré de `.gitignore` | `sed` sur `.gitignore` | `test_fichiers_de_base_ignores_par_git[sqlite-wal]` échoue (1 failed, 9 passed) |
| Restauration | `git -C <worktree> checkout -- .` ; `git status --short` ; `git rev-parse HEAD` | arbre propre, HEAD = 02eb02b6424e2c62af5d476367da0ed4e6b05c86 (un premier `checkout -- .` lancé depuis `02_Service` n'avait pas restauré `.gitignore`, corrigé depuis la racine) |
| Secrets, courriels | lecture du diff complet | aucun |
| Registres et plan | sans objet | aucun document créé |
| Pipeline locale `ci.sh --ref` | non lancée | CI GitHub verte (règle 10) |
| Rapports opus | lus après la vérification | concordants ; mes constats 1 à 4 recoupent leurs mineurs, aucun écart |

## Mandats de suite

Facultatif, à joindre au mandat « magasin SQLite concurrent » : clé de cache résolue, contrôle de `sqlite_master` plutôt que `exists()`, `lister_avec_identifiants` du module en lecture différée ou retiré, test de la branche « mode non WAL », test des règles Git sauté hors dépôt.
