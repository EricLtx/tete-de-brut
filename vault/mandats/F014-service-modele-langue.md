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
rendu_a:
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
| 2026-11-07 | réalisateur sonnet / medium | Correctif du doublage 724e646 (sha : tête de la branche après le commit `fix(resume)` ; run et nombre de tests dans le compte rendu au retour). Corrigé : (1) filtre propre à la sortie du modèle, `app/filtre_sortie.py` (préfixes désaccentués, tournures, décisions), consigne du rapport opus reprise, 16 textes refusés et 3 neutres testés ; (2) création de fiche dans `run_in_threadpool` et plafond global de 10 s sur l'appel (test de concurrence, test de dépassement avec ligne `resume.modele`) ; (3) `content` entier, `httpx.InvalidURL` : gabarit ; décisions insensibles aux accents, à la casse et à `ne_pas_amplifier` ; compteur de phrases robuste aux sauts de ligne et au « … » ; balises retirées, Markdown refusé ; `max_tokens` 1024. Non fait : `thinking` non envoyé, valeur `between_tools` du rapport non vérifiable ici, test `reel` à lancer par un humain. `app/base.py` : écart accepté par l'orchestrateur. |
