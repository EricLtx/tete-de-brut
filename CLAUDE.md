# CLAUDE.md — tete-de-brut

Instructions pour toute session Claude sur ce dépôt. Les sections 1 à 4 changent rarement : elles forment le
préfixe stable que le cache de prompt réutilise d'une session à l'autre ; mettre ce qui bouge souvent en fin de fichier.

## 1. Projet

« Tête de Brut. » : service d'API de la démonstration du hackathon Hack the Feed (piste éditoriale Brut, 07/11/2026). Il lit l'intérieur des vidéos sociales par Oriane (transcriptions, texte à l'écran), regroupe les récits, compare deux versions mot à mot et porte la fiche de vérification d'une rédaction. Trois écrans Lovable, hors dépôt, consomment son contrat OpenAPI `api.v1`. Ce dépôt public ne contient que le code et son harnais ; la documentation de cadrage (cahier des charges, business case, veille) reste dans un dépôt privé. Documentation en français. **Phase actuelle :** construction du service (plan `01_Docs/08_Plans/plan-service-demonstration.md`).

## 2. Carte du dépôt

| Chemin | Contenu |
|---|---|
| `02_Service/` | Le service : `app/` (FastAPI), `contrats/` (schémas JSON et `api.v1.json`), `tests/`, `scripts/`, `cas/` (cas enregistré, hors Git), `Dockerfile`, `pyproject.toml`, `.env.example` |
| `01_Docs/00_Index/` | Point d'entrée de la documentation : index, registre des décisions, registre de la documentation |
| `01_Docs/07_Decisions/` | Décisions structurantes (ADR) et gabarit ; ADR-0001 : périmètre et pile du service |
| `01_Docs/08_Plans/` | Plan de construction du service (fiches S01 à S10), à relire avant un mandat et à aligner à chaque étape |
| `01_Docs/05_Integration/` | Guide de branchement des écrans Lovable et d'Oriane sur le service |
| `01_Docs/04_CICD/` | Pipeline, gardes, intégration continue hébergée, règles d'efficience des mandats |
| `04_Pipeline/` | Pipeline locale : `ci.sh`, `build.sh`, `check-docs.sh`, `doctor.sh`, gardes git `hooks/` |
| `.github/workflows/` | Intégration continue GitHub : rejoue `04_Pipeline/ci.sh`, rien d'autre |
| `vault/` | Mandats (`mandats/`), rapports de doublage (`revues/`), journal machine (`runtime/`, hors Git) |
| `config/harnais.json` | Réglages du harnais : branche protégée, commandes de build et de contrôle, relecteur |

## 3. Règles non négociables

1. **La branche protégée (`main`) ne reçoit que du relu ou de la documentation.** Code : branche `feat/…`, `fix/…` ou `pipeline/…` depuis `main` à jour → push → workflow GitHub vert sur le sha (il rejoue `04_Pipeline/ci.sh`) → doublage (skill `harnais-doublage`, rapport GO dans `vault/revues/`) → `git merge --no-ff` → push. Documentation seule (`*.md`, `01_Docs/`, `vault/`) : commit direct sur `main`, push, workflow vert.
2. **Ne jamais contourner une garde** (`04_Pipeline/ci.sh`, hooks `pre-commit`, `commit-msg`, `pre-merge-commit`, `pre-push`, workflow GitHub) : ni `--no-verify`, ni seuil abaissé, ni contrôle désactivé. Corriger la cause.
3. **Aucun secret ni donnée personnelle dans le dépôt** : clés, `.env`, exports, comptes de service, adresses de courriel, cas réel enregistré (comptes et propos de personnes publiques : `02_Service/cas/` reste hors Git et voyage dans l'image). Les gardes refusent les motifs de `config/harnais.json → interdits` ; `pipeline.controles` refuse toute adresse de courriel. Les tests n'utilisent que des vidéos simulées.
4. **Décisions structurantes** (nouvelle dépendance, nouvelle source de données, contrat d'API, hébergement) : ADR au statut « Proposée » dans `01_Docs/07_Decisions/`, ligne dans le registre des décisions, même commit. Ne pas trancher seul. La pile est close (ADR-0001) : Python, FastAPI avec pydantic, uvicorn, httpx, SQLite de la bibliothèque standard, pytest, ruff ; toute autre dépendance révise l'ADR, jamais un mandat.
5. **Tout nouveau document** est inscrit dans `01_Docs/00_Index/registre-documentation.md` dans le même commit ; tout plan actif est réaligné (journal d'alignement) à chaque étape terminée.
6. **Une tâche = un mandat = un commit** (skill `harnais-mandat`) : fichier dans `vault/mandats/`, modèle et effort nommés, critère de fin testable, fichiers réservés. Le sous-agent travaille dans un worktree `.claude/worktrees/<branche>`.
7. **Ne jamais commiter, écarter ni écraser les fichiers non commités d'une autre session.** Le stash est partagé entre worktrees : pas de `git stash` nu.
8. **Règles de confiance du service, testées à chaque mandat** : aucun champ de tiers d'Oriane n'entre en base ni au journal (liste blanche `app/liste_blanche.py`) ; aucun libellé refusé (faux, première, originale, manipulé, coordonné, déformé, et leurs accords) dans un segment `libelle` d'une réponse ; chaque mesure porte `methode` et `fenetre` ; chaque réponse JSON porte `mode` (`direct` ou `enregistre`) et, en mode enregistré, `enregistre_le` ; chaque transcription est attribuée à Oriane ; aucun test n'appelle le réseau (`httpx.MockTransport`) ; les tests réels, marqués `reel`, sont sautés sans clé.
9. **Mandat court, qui renvoie.** Un mandat de code tient en 250 mots : il renvoie à sa fiche `Sxx` du plan et cite le contrat qu'il touche (`02_Service/contrats/`) sans les recopier ; tout ce qui n'y figure pas est hors mandat. Chaque mandat a son fichier `02_Service/tests/test_<module>.py` ; les réponses Oriane simulées vivent dans `tests/conftest.py` et se réutilisent, jamais ne se redéfinissent. Le réalisateur n'écrit pas dans le fichier de mandat : il rend cinq lignes (sha, `git diff --stat`, dernière ligne de `ci.sh --ref`, écarts, points ouverts).
10. **Pas de pipeline locale tant que la CI GitHub tient, un correctif léger.** `pipeline.ci` est vide : la garde `pre-push` ne rejoue pas les tests, elle ne vérifie que le GO et la règle de documentation seule. Le réalisateur commite, pousse et lit le résultat du workflow (`gh run list --branch <branche> --limit 1`) ; il ne lance `04_Pipeline/ci.sh` à la main que si GitHub ne répond pas ou pour reproduire un échec. Le relecteur de `config/harnais.json` (`sonnet` / high) suffit à un mandat mécanique ; un mandat de conception (contrat, textes lus par le jury) demande `opus` dans son champ `relecteur`, jamais moins que la config. Un NO-GO part en correctif `sonnet` / low, relu sur le seul diff entre les deux sha. Détail : `01_Docs/04_CICD/pipeline-cicd.md`, § 4.

## 4. Commandes

```bash
04_Pipeline/doctor.sh      # outils et gardes du poste
04_Pipeline/ci.sh          # pipeline locale, à la main seulement (la CI GitHub la rejoue à chaque push)
gh run list --branch <branche> --limit 1   # résultat du workflow sur le dernier push
04_Pipeline/build.sh       # build et contrôles du code (commandes de config/harnais.json)
04_Pipeline/check-docs.sh  # markdownlint + liens locaux (lychee hors ligne, natif ou par Docker)
git config core.hooksPath 04_Pipeline/hooks   # activer les gardes (une fois par clone et par worktree)
cd 02_Service && python -m pip install -e ".[dev]"            # dépendances du service (à partir de S01)
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q
cd 02_Service && python -m uvicorn app.main:app --port 8080  # service local ; variables dans .env.example
```

## 5. État courant (section vivante, mise à jour par les plans)

Dépôt créé et équipé le 07/11/2026 (canon 1.0.3, workflow GitHub qui rejoue `ci.sh`). Plan actif : `01_Docs/08_Plans/plan-service-demonstration.md` ; ADR-0001 acceptée le 07/11 ; licence commerciale « Tête de Brut. » (`LICENSE`). Construction lancée : mandat F002 (S01, `feat/service-socle`). Prochaine porte : S02 dès S01 rendu, jonction 1 à 12 h, jonction 2 et gel à 15 h 30.

## Harnais (ajouté par le plugin harnais-pipeline)

<!-- harnais-pipeline:debut -->
- **Circulation du travail** : une tâche = un mandat dans `vault/mandats/` (skill `harnais-mandat`), réalisé par un sous-agent dans un worktree, puis relu par une instance distincte (skill `harnais-doublage`, modèle imposé par `config/harnais.json → relecteur`) qui écrit un rapport dans `vault/revues/`. **La fusion dans la branche protégée exige un rapport « verdict: GO » sur le dernier commit de la branche** : les gardes `pre-merge-commit` et `pre-push` le vérifient. Documentation seule : commit direct sur la branche protégée.
- **Gardes git** (`04_Pipeline/hooks/`, activées par `git config core.hooksPath 04_Pipeline/hooks`) : `pre-commit` (taille, secrets, conflits), `commit-msg` (`type(portée): sujet`), `pre-merge-commit` et `pre-push` (pipeline + GO). Aucun contournement : corriger la cause.
- **Journal machine** : `vault/runtime/events.jsonl` (hors Git), écrit par la pipeline et les gardes ; l'orchestrateur le lit au lieu de relire le chat.
- **Capacité** : l'orchestrateur écrit les mandats, lit le journal, lance le doublage et fusionne ; il ne code pas et ne rédige pas de long document lui-même. Le modèle et l'effort de chaque sous-agent suivent la difficulté de la tâche (`opus` conception et textes, `sonnet` implémentation spécifiée, `haiku` tri).
- **Canon** : ce bloc, les gardes et `04_Pipeline/lib/` viennent du plugin `harnais-pipeline` (version dans `config/harnais.json → canonVersion`). Les mettre à jour par le skill `harnais-pipeline` (auditer puis équiper), pas à la main.
<!-- harnais-pipeline:fin -->
