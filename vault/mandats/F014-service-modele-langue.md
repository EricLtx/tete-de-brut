---
mandat: F014
titre: S10 — Résumé de fiche par modèle de langue (Claude), filtré, enregistré avec le cas
statut: lance
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S10
branche: feat/service-modele-langue (part de main)
worktree: .claude/worktrees/feat-service-modele-langue
modele: opus
effort: medium
relecteur: opus / medium (textes lus par le jury), jamais moins que la config
cree: 2026-11-07
lance_a: 2026-11-07T13:34Z
rendu_a: 2026-11-07T13:47Z
go_a:
allers_retours: 0
---

# F014 — S10, résumé par modèle de langue

**Bloqué tant que l'ADR-0002 n'est pas Acceptée** (règle 4) : ne pas lancer avant.

## Objectif

`resumer` aiguille vers un résumé rédigé par Claude quand `RESUME_MODE=modele` (signature inchangée, voir `app/resume.py`), sinon le gabarit. Appel par `httpx` (aucune dépendance), configuration `MODELE_LANGUE_URL`, `MODELE_LANGUE_API_KEY`, `MODELE_LANGUE_ID` (remplacent `SCALEWAY_*`).

## Règles

Fiche S10 du plan et ADR-0002 : seuls les extraits `citation` partent, entre délimiteurs ; sortie passée au filtre des libellés refusés ; résumé marqué « rédigé par un modèle de langue, à relire » ; aucun constat ni décision rédigé ; échec, refus ou libellé refusé : gabarit et ligne au journal ; résumé enregistré avec la fiche.

## Fichiers réservés

`app/modele_langue.py` (nouveau), `app/resume.py`, `app/config.py`, `.env.example`, `tests/test_modele_langue.py` (nouveau). Réponses simulées par `httpx.MockTransport` ; un test `reel` sauté sans `MODELE_LANGUE_API_KEY`. Consigne piégée dans une citation : sans effet.

## Commande de fin et sortie attendue

Run `pipeline` vert sur le sha ; tests de la fiche S10 verts.

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat` ; run ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | orchestrateur (session service) | ADR-0002 acceptée par le propriétaire ; lancé sur `feat/service-modele-langue` (worktree `.claude/worktrees/feat-service-modele-langue`), réalisateur opus / medium. Modèle visé : `claude-sonnet-5-5` par l'API Messages d'Anthropic ; la clé locale `MODELE_LANGUE_API_KEY` est posée par le propriétaire dans `02_Service/.env`, le secret GitHub `ANTHROPIC_API_KEY` existe déjà. |
| 2026-11-07 | réalisateur opus / medium | Rendu 7244d81968f1de7649134aa679f99d8b44c63133 : `app/modele_langue.py` (+150, API Messages par httpx, `output_config.effort=low` à la place de `temperature` refusée par Sonnet 5.5, texte lu dans le premier bloc `text`), `app/resume.py`, `config.py` (`RESUME_MODE` validé, `MODELE_LANGUE_*`, champs Scaleway retirés), `.env.example`, `tests/test_modele_langue.py` (+320, 22 tests) ; run 42378464799 vert, 324 tests ; test `reel` sauté (clé absente du poste). Filtres : libellés refusés, valeurs de décision, plus de quatre phrases, `stop_reason` refus ou `max_tokens`, réponse vide → gabarit et journal `resume.modele`. Limites : 400 jetons, 12 extraits de 40 mots, 10 s, appel synchrone dans `POST /v1/fiches`. Correctif demandé avant doublage : `VARIABLES_SECRETES` de `app/base.py` à aligner sur `MODELE_LANGUE_API_KEY` (test), repli sur `ANTHROPIC_API_KEY`. |
