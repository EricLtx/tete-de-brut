---
mandat: F001
titre: Équipement du dépôt public Tête de Brut (canon 1.0.3, workflow GitHub, réglages d'efficience, plan et ADR transposés)
statut: fusionne
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: équipement (avant S01)
branche: pipeline/harnais
worktree: aucun (dépôt neuf, aucune autre session ; écart déclaré)
modele: orchestrateur (scripts du canon lancés tels quels) ; sonnet / medium pour la transposition du plan et de l'ADR
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T08:40Z
rendu_a: 2026-11-07T09:35Z
go_a: 2026-11-07T09:52Z
allers_retours: 1
---

# F001 — Équipement du dépôt public

## Objectif

Le dépôt public « Tête de Brut » porte le harnais (canon 1.0.3), un workflow GitHub qui rejoue `04_Pipeline/ci.sh`, des réglages tirés de la revue des mandats du dépôt de cadrage, le plan de construction du service et l'ADR-0001, pour que le mandat S01 puisse partir.

## Fichiers réservés

`config/harnais.json`, `CLAUDE.md`, `.github/workflows/pipeline.yml`, `lychee.toml`, `.markdownlint-cli2.jsonc`, `04_Pipeline/**`, `vault/README.md`, `vault/mandats/0000-gabarit-mandat.md`, `vault/revues/0000-gabarit-revue.md`, `01_Docs/**`, `README.md` (mise en conformité de lint), ce mandat.

## État du poste

Python 3.13, Docker 29 (lychee par conteneur), Node présent, réseau ouvert, aucune clé Oriane sur le poste.

## Commande de fin et sortie attendue

```bash
04_Pipeline/doctor.sh                  # « Poste et dépôt prêts »
gh run list --branch pipeline/harnais --limit 1   # workflow « pipeline » : success sur le dernier sha
git commit --allow-empty -m "message sans type"   # refusé par commit-msg
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat origin/main...HEAD` ; dernière ligne de `ci.sh --ref` ; écarts à la fiche ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | orchestrateur | Audit : 25 absents, 0 divergent (dépôt neuf). Équipement par `equiper.sh --projet tete-de-brut` ; `canonVersion` corrigé à 1.0.3 (gabarit du canon en 1.0.2, retour consigné). Réglages : relecteur `sonnet` / high, build guardé tant que `02_Service/` n'existe pas, contrôle anti-courriel, `docsSeulement` sans les configs de lint, types de commit réduits, lychee hors ligne. Plan et ADR transposés par un sous-agent `sonnet` depuis le dépôt privé, avec les compléments de contrat de la revue d'architecture (préfixe `/v1`, enveloppe d'erreur, `snake_case` français, `ORIANE_DELAI_S`, `CLE_DEMO`, comparaisons idempotentes). Écart : orchestrateur sans worktree (dépôt neuf). Point ouvert : licence du dépôt public (registre des décisions). |
| 2026-11-07 | relecteur sonnet / high | GO sur fabe22f : 0 bloquant, 1 majeur (`README.md` hors réserve), 4 mineurs ; doctor, ci (189 s), garde commit-msg, JSON, grep courriel rejoués. |
| 2026-11-07 | orchestrateur | Majeur accepté : `README.md` ajouté à la réserve (correction de lint du titre, même mandat). Demande du propriétaire reçue pendant le doublage : pas de pipeline locale tant que la CI GitHub fonctionne ; `pipeline.ci` vidé, règles 1 et 10 du CLAUDE.md et `pipeline-cicd.md` adaptés, la relecture vérifie le run GitHub sur le sha. Nouveau sha : second doublage sur le seul diff. Mineurs du plan (uvicorn et pydantic « à confirmer », `pytest -q` sans `-m 'not reel'`) corrigés dans le même commit. |
| 2026-11-07 | orchestrateur | Second doublage : GO sur f604024 (0 bloquant, 0 majeur, 3 mineurs, 1 min). Rapports posés sur `main`, fusion `--no-ff` 21d6076, branche supprimée. Mineur ouvert pour le propriétaire : protection de la branche `main` sur GitHub exigeant le job `ci` (aucune garde locale ne force plus la pipeline). |
