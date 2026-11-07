---
mandat: F014
titre: S10 — Résumé de fiche par modèle de langue (Claude), filtré, enregistré avec le cas
statut: fusionne
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
go_a: 2026-11-07T14:52Z
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
| 2026-11-07 | réalisateur opus / medium | Rendu 7244d81968f1de7649134aa679f99d8b44c63133 : `app/modele_langue.py` (+150, API Messages par httpx, `output_config.effort=low` à la place de `temperature` refusée par Sonnet 5.5, texte lu dans le premier bloc `text`), `app/resume.py`, `config.py` (`RESUME_MODE` validé, `MODELE_LANGUE_*`, champs Scaleway retirés), `.env.example`, `tests/test_modele_langue.py` (+320, 22 tests) ; run 42378464799 vert, 324 tests ; test `reel` sauté (clé absente du poste). Filtres : libellés refusés, valeurs de décision, plus de quatre phrases, `stop_reason` refus ou `max_tokens`, réponse vide → gabarit et journal `resume.modele`. Limites : 400 jetons, 12 extraits de 40 mots, 10 s, appel synchrone dans `POST /v1/fiches`. Correctif demandé avant doublage : `VARIABLES_SECRETES` de `app/base.py` à aligner sur `MODELE_LANGUE_API_KEY` (test), repli sur `ANTHROPIC_API_KEY`. |
| 2026-11-07 | réalisateur sonnet / medium | Correctif rendu 724e646c606068bee85c18ff3fc8f67fa98e32b7 : filtre des secrets du journal (`VARIABLES_SECRETES` dans `app/base.py`, hors réserve, déclaré) ; run 42378721637 vert, 327 tests. Doublage lancé (opus / high imposé par le mandat, plus sonnet / high pour la garde). |
| 2026-11-07 | relecteur opus / high | GO conditionnel sur 724e646c606068bee85c18ff3fc8f67fa98e32b7 (`vault/revues/F014-724e646-opus.md`) : 0 bloquant, 2 majeurs (douze synonymes passent le filtre de sortie du modèle : « trompeuse », « truquée », « falsifié », « mensonger », « détourné », « altérée », « déformation », « manipulation », « falsification », « sorti de son contexte », « cherche à faire croire », « change donc le sens » ; `app/base.py` hors réserve), 7 mineurs (extraits recopiés, filtre des décisions, compteur de phrases, réflexion active comptée dans les 400 jetons, attente de 10 s). Décision de l'orchestrateur : pas de fusion avec majeurs, correctif sur la même branche, relecture du diff. |
| 2026-11-07 | relecteur sonnet / high | GO conditionnel sur 724e646c606068bee85c18ff3fc8f67fa98e32b7 (`vault/revues/F014-724e646-sonnet.md`) : 0 bloquant, 2 majeurs (client HTTP synchrone dans la route `async` : un `GET /sante` concurrent retardé de 2 s, délai par phase ; `base.py` hors réserve), 4 mineurs (`content` liste → 500, `InvalidURL` non attrapé ; filtre des décisions sans désaccentuation ; compteur de phrases contournable, sortie non assainie ; configuration injectée ignorée). Aucune fuite de clé, quatorze mutations retombent sur le gabarit. Correctif unique demandé pour les deux rapports. |
| 2026-11-07 | orchestrateur (session service) | Correctif poussé par le réalisateur : 0021d2e5e2da5c4338a73d58a6dc3709324b9ae6 (`app/filtre_sortie.py`, appel hors de la boucle avec plafond global de 10 s, mineurs pris, `max_tokens` 1024, `thinking` non envoyé), run 42380635333 vert, 363 tests. Relecture du diff relancée auprès des deux relecteurs (opus pour le filtre, sonnet pour la garde). |
| 2026-11-07 | relecteur sonnet / high | GO sur 0021d2e5e2da5c4338a73d58a6dc3709324b9ae6 (`vault/revues/F014-0021d2e-sonnet.md`) : 0 bloquant, 0 majeur, 4 mineurs (« premier tour » et « contexte » refusés ; filtre lexical : « montage », « inversé », « erronée », « hoax » passent ; « … » hors du compte de phrases, fil orphelin après expiration ; configuration injectée ignorée, `thinking` non envoyé, API réelle non vérifiée). Rejoué : `/sante` plus retardé, expiration à 10,04 s avec ligne au journal, aucune fuite de clé. |
| 2026-11-07 | relecteur opus / high | NO-GO sur 0021d2e5e2da5c4338a73d58a6dc3709324b9ae6 (`vault/revues/F014-0021d2e-opus.md`) : 0 bloquant, 2 majeurs (le test de concurrence passe aussi sans `run_in_threadpool`, chrono démarré trop tard ; treize qualifications passent encore : « originelle », « authentique », « la vraie », « erroné », « inexacte », « décontextualisé », « trafiquée », « bidonné », « infox », « biaisé », « a menti », « altération », « sens modifié »), 4 mineurs. Décision de l'orchestrateur : second correctif par le même réalisateur, relecture du diff par opus ; la fusion attend. Le mode `gabarit` reste le défaut de la démonstration. |
| 2026-11-07 | réalisateur sonnet / medium | Second correctif 3b78e30b7e7ed0345d6908bee20a591874c8810f (`filtre_sortie.py`, tests : chrono avant `create_task`, test vu échouer sans `run_in_threadpool` ; treize qualifications de plus refusées, mots entiers `vrai`, `menti`), run 42381374549 vert, 377 tests. |
| 2026-11-07 | relecteur opus / high | GO sur 3b78e30b7e7ed0345d6908bee20a591874c8810f (`vault/revues/F014-3b78e30-opus.md`) : majeurs levés (sonde de 40 textes propre, test de concurrence qui échoue sans le correctif), 0 bloquant, 0 majeur, 3 mineurs (tournures sur mots contigus seulement ; faux positifs assumés « origine », « par le biais de », « premier tour » ; mineurs antérieurs acceptés). Test `reel` à lancer par une personne sur le cas réel. |
| 2026-11-07 | relecteur sonnet / high | GO sur 3b78e30b7e7ed0345d6908bee20a591874c8810f (`vault/revues/F014-3b78e30-sonnet.md`) : 0 bloquant, 0 majeur, mineurs inchangés (préfixes larges, filtre lexical, fil orphelin, configuration injectée, `thinking`). Fusionné sur `main`. |
