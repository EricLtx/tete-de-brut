---
mandat: F001
branche: pipeline/harnais
commit: fabe22f170c758d9092590fbca700c1011d174e8
relecteur: sonnet
effort: high
verdict: GO
date: 2026-11-07
---

# Doublage F001 — Équipement du dépôt public

## Verdict

GO : le sha relu est la tête de `pipeline/harnais`, `doctor.sh` et `ci.sh --ref pipeline/harnais` sont verts (rejoués, 189 s), la garde `commit-msg` refuse un message sans type, scripts et gardes sont en 100755, l'arbre ne contient ni courriel, ni clé, ni nom de personne, ni chemin privé du poste ; aucun bloquant, un écart de réserve (majeur, non bloquant) et trois mineurs.

## Constats

| Gravité | Emplacement | Constat | Remède |
|---|---|---|---|
| Majeur | `README.md` (commit `fabe22f`) | Fichier modifié (titre sans point final, règle MD026) mais absent de la réserve du mandat, qui ne cite pas `README.md`. Le changement est nécessaire à un `ci.sh` vert et sans risque (documentation seule). | Ajouter `README.md` aux fichiers réservés de F001 au passage à `go` (ou le consigner dans les Échanges) ; pas de correctif de code. |
| Mineur | Métadonnées des deux commits de la branche (et de `origin/main`) | L'adresse de courriel personnelle de l'auteur figure dans les métadonnées Git (auteur et committer). Hors arbre, donc hors du contrôle `pipeline.controles`, et déjà présente sur `origin/main` : non introduite par cette branche. Le dépôt étant public, elle sera visible. | Décision de l'équipe : adresse de remplacement fournie par l'hébergeur (`git config user.email`) pour les commits suivants ; la réécriture de l'historique déjà poussé est à arbitrer par le propriétaire, pas par ce mandat. |
| Mineur | Plan, section « Modules et fichiers réservés » (ligne 45) et ADR-0001, règle 3 ; `CLAUDE.md` § 3 règle 4 | La pile « close » nomme `uvicorn` et `pydantic` dans l'ADR et `CLAUDE.md`, alors que le plan les marque « à confirmer » en dehors de sa liste. Pas de contradiction sur une dépendance hors pile (aucune autre bibliothèque n'apparaît dans le plan), mais deux formulations. | Aligner la phrase du plan sur l'ADR au prochain alignement (S01 confirme les versions). |
| Mineur | Plan, fiche S01 (colonne fichiers) et `config/harnais.json → pipeline.build` | La fiche S01 cite `python -m pytest -q`, la config porte `python -m pytest -q -m 'not reel'`. | S01 reprend la commande de la config (la règle 8 de `CLAUDE.md` prévoit le marqueur `reel`). |
| Mineur | `config/harnais.json → docsSeulement` | Contient `.claude/` et ses exceptions `!.claude/skills/`, `!.claude/*.json` : ni code ni pipeline, conforme ; la présence de ces entrées est sans effet tant que ces chemins n'existent pas. Sans suite requise. | Aucun. |

## Vérifications faites

| Vérification | Commande | Résultat |
|---|---|---|
| Sha relu = tête de branche | `git rev-parse pipeline/harnais` ; `git rev-parse HEAD` dans le worktree | `fabe22f170c758d9092590fbca700c1011d174e8` des deux côtés ; worktree propre après les rejeux |
| Commits | `git log --oneline origin/main..fabe22f…` | 2 commits : `3e6acfd pipeline(harnais): équipement du dépôt, workflow GitHub, plan du service et ADR-0001` ; `fabe22f docs(readme): titre sans ponctuation finale (règle MD026)`. Types valides, aucun fichier interdit |
| Périmètre | `git diff --stat origin/main...fabe22f…` | 30 fichiers, +1127 −1. Tous dans la réserve (`config/`, `CLAUDE.md`, `.github/workflows/`, `lychee.toml`, `.markdownlint-cli2.jsonc`, `04_Pipeline/**`, `vault/**` cités, `01_Docs/**`, mandat) sauf `README.md` (voir constat majeur) |
| Modes dans l'index | `git ls-files -s 04_Pipeline` | `ci.sh`, `build.sh`, `check-docs.sh`, `doctor.sh` et les 4 gardes de `hooks/` : 100755 ; `lib/*.sh` : 100644 (sourcés). Aucun autre mode anormal dans l'arbre |
| Poste et gardes | `bash 04_Pipeline/doctor.sh` (worktree) | Tous les contrôles cochés (git, python, node, lychee, config, hooks actifs, 4 gardes, vault, registres) ; « Poste et dépôt prêts » ; 2,7 s |
| Pipeline locale | `bash 04_Pipeline/ci.sh --ref pipeline/harnais` (worktree) | markdownlint : 15 fichiers, 0 problème ; lychee : 27 liens, 27 OK, 0 erreur ; build 1 et 2 sans service (gardés) ; contrôle anti-courriel passé ; `code OK`, `docs OK`, « Pipeline locale verte » ; sortie 0 ; durée 189 s |
| Garde commit-msg | `git commit --allow-empty -m "message sans type"` (worktree) | Refusé : « Message de commit non conforme » ; code 1 ; HEAD inchangé (aucun `reset` nécessaire) |
| JSON de config | `python -c "import json;json.load(open('config/harnais.json',encoding='utf-8'))"` | « json ok » |
| Courriel dans l'arbre | `git grep -nIE '[[:alnum:]._%+-]+@[[:alnum:].-]+[.][[:alpha:]]{2,}' fabe22f…` | Aucune occurrence (code retour 1) |
| Chemins privés, clés, noms | `git grep -nIiE 'C:[\\/]+Users\|/c/Users\|OneDrive\|AppData\|/home/…'`, `git grep -nIiE '(api[_-]?key\|secret\|token\|password\|bearer\|sk-…)'` hors `04_Pipeline`, recherche de noms de personnes et du compte GitHub | Aucun chemin privé, aucun nom de personne dans l'arbre. Les mots « secret / clé / token » n'apparaissent que comme noms de variables (`ORIANE_API_KEY`, `SCALEWAY_API_KEY`, `CLE_DEMO`) et règles, sans aucune valeur ; fichiers interdits (`.env`, `*.csv`, `*.sqlite`, `*.pem`, `*.key`) absents de l'index |
| Métadonnées de commit | `git log --format=… origin/main..fabe22f…` | Auteur et committer « unknown » ; courriel personnel présent (voir constat mineur) |
| `config/harnais.json` | lecture | `docsSeulement` : documentation, vault, `.claude/` (avec exceptions), `CLAUDE.md`, `README.md` ; ni code, ni pipeline, ni `.github/`, `lychee.toml`, `.markdownlint-cli2.jsonc`. `interdits` complets (`.env*` avec exception `.env*.example`, `*.pem`, comptes de service, `*.csv`, `*.key`, bases SQLite, cas réel). `relecteur` : sonnet / high. Build guardé `test ! -d 02_Service \|\| …` (ruff puis pytest `-m 'not reel'`) ; contrôle anti-courriel présent et bloquant (`exit 1`) |
| Workflow | lecture de `.github/workflows/pipeline.yml` | Une seule commande métier : `bash 04_Pipeline/ci.sh --ref "$REF"` (sha de PR ou de push) ; `fetch-depth: 0` ; dépendances du service installées seulement si `02_Service/pyproject.toml` existe ; `permissions: contents: read` ; Python 3.12, Node 20. Non exécuté sur GitHub (non faite) |
| `lychee.toml`, lint | lecture | `offline = true`, exclusions de `.claude/worktrees` ; `.markdownlint-cli2.jsonc` ignore `.claude/worktrees/**` |
| `CLAUDE.md` | lecture | Section 5 « État courant » en dernier avant la section Harnais ; bloc du plugin conservé entre `harnais-pipeline:debut` et `harnais-pipeline:fin`, texte conforme à celui du dépôt de cadrage ; règles 1 à 10 présentes |
| Gabarit de mandat et § 4 CICD | lecture de `vault/mandats/0000-gabarit-mandat.md` et `01_Docs/04_CICD/pipeline-cicd.md` | Gabarit : champs `lance_a`, `rendu_a`, `go_a`, `allers_retours`, renvoi à la fiche, cinq lignes de compte rendu. § 4 : règles d'efficience conformes à `CLAUDE.md` règles 9 et 10 et à la config (relecteur, un seul `ci.sh`, mandat de 250 mots) |
| Plan et ADR | lecture de `plan-service-demonstration.md` (sections, contrat, « Compléments de contrat » a à g, fiches S01 à S10) et de l'ADR-0001 | Compléments (préfixe `/v1`, enveloppe d'erreur, `snake_case` français, `ORIANE_DELAI_S`, `CLE_DEMO`, idempotence, état, pas de passerelle) repris dans l'ADR (Conséquences) et dans la fiche S01 ; pile close identique (ADR, `CLAUDE.md`, plan) ; aucune dépendance hors pile dans le plan ; règle 7 de l'ADR cohérente avec `CLAUDE.md` règle 4. Liens relatifs du plan et de l'ADR : 3 liens, vers des fichiers existants (confirmé aussi par lychee : 27/27) |
| Registres | lecture de `registre-documentation.md`, `registre-decisions.md`, `08_Plans/README.md` | Les 9 fichiers de `01_Docs/` sont inscrits au registre de la documentation (y compris les deux README de dossiers, le gabarit de plan, la CICD) ; ADR-0001 au registre des décisions (Proposée) ; plan dans `08_Plans/README.md` (Actif) |
| Lecture du canon | non faite | Hors périmètre de la relecture, comme demandé (scripts, gardes, `lib/`, gabarits copiés) ; seule leur exécution et leurs modes ont été contrôlés |
| Exécution du workflow sur GitHub, lychee en ligne | non faite | Impossible depuis le poste ; lychee a tourné hors ligne par Docker |

Durée de `ci.sh --ref pipeline/harnais` : 189 s. Durée totale de la relecture : environ 4 min.

## Mandats de suite

Aucun mandat de correctif. Trois actions documentaires, sans passer par une branche de code :

- Consigner `README.md` dans la réserve de F001 (Échanges du mandat, commit direct de documentation) avant le passage à `go`.
- Arbitrer le courriel des métadonnées de commit pour le dépôt public (décision du propriétaire, avant la publication du dépôt).
- Au démarrage de S01 : aligner la phrase du plan sur la pile close de l'ADR (uvicorn, pydantic) et reprendre la commande pytest de la config.
