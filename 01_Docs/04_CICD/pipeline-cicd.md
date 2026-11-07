# Pipeline locale et gardes git

> Conception de la pipeline du dépôt, installée par le plugin `harnais-pipeline` (canon 1.0.3). Les contrôles sont écrits pour le poste (`04_Pipeline/ci.sh`, worktree propre) mais tournent sur GitHub après chaque push (`.github/workflows/pipeline.yml`, même script, aucun contrôle propre) : `pipeline.ci` est vide, la garde `pre-push` ne rejoue pas la pipeline localement tant que la CI GitHub fonctionne (décision du propriétaire, 07/11/2026). Le bloc « Harnais » du `CLAUDE.md`, texte du canon, décrit `pre-push` avec pipeline : ici elle est désactivée par la config, pas par une modification de la garde.

## 1. Contrôles

| Contrôle | Script | Quand | Bloquant | Exigence couverte |
|---|---|---|---|---|
| Build et contrôles du code (`pipeline.build`, `pipeline.controles` de `config/harnais.json`) | `04_Pipeline/build.sh` | `ci.sh` sur GitHub à chaque push, si la branche touche du code | Oui | Le code livré compile et passe ses tests |
| Lint Markdown et liens | `04_Pipeline/check-docs.sh` | `ci.sh` sur GitHub à chaque push, si la branche touche de la documentation | Oui | Documentation lisible, liens valides |
| Taille des fichiers, secrets, marqueurs de conflit | `hooks/pre-commit` | Chaque commit | Oui | Aucun secret ni donnée personnelle dans Git |
| Forme du message | `hooks/commit-msg` | Chaque commit | Oui | Historique lisible par type |
| Rapport de doublage GO sur le commit fusionné | `hooks/pre-merge-commit`, `hooks/pre-push` | Fusion et push vers la branche protégée | Oui | Rien n'entre dans la branche protégée sans relecture indépendante |
| Commit direct limité à la documentation | `hooks/pre-push` | Push vers la branche protégée | Oui | Le code passe par une branche relue |

## 2. Réglages

`config/harnais.json` : branche protégée, chemins « documentation seule », taille maximale, motifs interdits, types de commit, commandes de build et de contrôle, relecteur imposé, dossiers du vault.

## 3. Journal

`vault/runtime/events.jsonl` (hors Git) : une ligne par événement (`ci`, `push`, `merge`, `mandat`, `doublage`), lue par l'orchestrateur et par le hook de session du plugin.

## 4. Intégration continue hébergée et efficience des mandats

**Workflow GitHub.** `.github/workflows/pipeline.yml` exécute `bash 04_Pipeline/ci.sh --ref <sha>` sur chaque push et chaque pull request (historique complet, Python 3.12, Node 20 pour markdownlint, lychee par Docker). Il installe `02_Service[dev]` quand le service existe. Local et distant ne peuvent pas diverger : il n'y a qu'un script. `lychee.toml` est en mode hors ligne : seuls les liens relatifs vers des fichiers du dépôt sont vérifiés.

**Réglages tirés de la revue des mandats du dépôt de cadrage (07/11/2026).** Seize mandats et quatre doublages relus : les bloquants trouvés relevaient de contrôles mécaniques (modes de fichiers, adresses de courriel, noms de personnes), le doublage `opus` / high aurait représenté plus de la moitié du temps de réalisation estimé des mandats de code (E), `ci.sh` était lancé deux fois avant dix push sur dix-neuf, un correctif prescrit en `sonnet` / low est reparti en `opus`, l'environnement (lychee, réseau) a été découvert en cours de mandat. D'où :

| Règle | Détail | Pourquoi |
|---|---|---|
| Relecteur `sonnet` / high par défaut | `config/harnais.json → relecteur` ; un mandat de conception (contrat, textes lus par le jury) exige `opus` dans son champ `relecteur` ; jamais moins que la config | Le doublage ne doit pas coûter plus que la réalisation d'un mandat mécanique |
| Ordre de relecture d'un mandat de code | 1. sha relu = tête de la branche ; 2. diff dans la réserve ; 3. workflow GitHub vert sur ce sha (`gh run list --commit <sha>`), `ci.sh --ref` rejoué seulement s'il manque ; 4. commande du critère de fin ; 5. un test par ligne « Refuse » de la fiche ; 6. aucun secret ni courriel. Le relecteur saute le canon, les registres et le style (ruff) | Vérifier d'abord ce qui a bloqué par le passé |
| Correctif après NO-GO | `sonnet` / low, même réalisateur s'il a encore son contexte ; relu sur le seul diff entre les deux sha | Un correctif n'est pas une réécriture |
| Pas de pipeline locale | `pipeline.ci` vide : ni le réalisateur, ni `pre-push`, ni l'orchestrateur ne lancent `ci.sh` ; le workflow GitHub fait foi sur chaque sha ; `ci.sh` à la main seulement si GitHub ne répond pas ou pour reproduire un échec | Quatorze exécutions inutiles relevées au journal (E) ; un run GitHub coûte 30 s à 3 min sans occuper le poste |
| Mandat de 250 mots, horodaté | Gabarit `vault/mandats/0000-gabarit-mandat.md` : renvoi à la fiche, état du poste, commande de fin, `lance_a`, `rendu_a`, `go_a`, `allers_retours` | Mesurer ce que coûte un mandat pour ajuster modèle et effort au plan suivant |
| Prompt du réalisateur | La fiche `Sxx` telle quelle, les chemins de `contrats/api.v1.json` et de `tests/conftest.py`, l'état du poste, les commandes exactes, une ligne d'attribution ; il commite lui-même et rend cinq lignes ; il n'écrit pas dans le mandat | Éviter les allers-retours et les conflits sur le fichier de mandat |
| Mandats enchaînés sans attendre la fusion | S02 peut partir de la branche de S01 dès que S01 est rendu (fusion de S02 après celle de S01) ; S06 peut suivre S05 sur sa branche, par le même réalisateur, s'il est rendu avant 11 h 15 (H), avec un seul doublage | Sortir le doublage de S01 du chemin critique (≈ 15 min, E) ; un doublage de moins |
| Journal des branches | `HARNAIS_ROOT` pointe sur le dépôt principal quand `ci.sh` tourne dans un worktree (sinon les événements disparaissent avec lui) | Observation faite sur le dépôt de cadrage ; à porter au canon |
