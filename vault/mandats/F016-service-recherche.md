---
mandat: F016
titre: S13 — Recherche à la demande : question ou lien collé traduits en filtres affichés avant lancement, coût estimé, exécution chez Oriane, récit ajouté au radar (POST /v1/recherches/preparer, POST /v1/recherches)
statut: en-doublage
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S13
branche: feat/service-recherche (part de main)
worktree: .claude/worktrees/feat-service-recherche
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T13:58Z
rendu_a: 2026-11-07T14:20Z
go_a:
allers_retours: 0
---

# F016 — S13, recherche à la demande

Décision de l'équipe du 07/11 (13 h 40) : la recherche par le système est au même rang que le radar, les versions et la fiche (cahier v1.1 : US-01, US-02, US-10, US-11, RG-02, FN1, FN4). **Fin d'implémentation visée : 15 h 20.** Le mandat renvoie au contrat `02_Service/contrats/`, à `app/oriane.py` (`rechercher`), `app/acquisition.py` (écriture des vidéos, calcul des récits et du coût), `app/recits.py`, `app/securite.py` ; il ne les recopie pas.

## Objectif

Deux routes sous `/v1`, derrière `X-Cle-Demo` :

1. `POST /v1/recherches/preparer` corps `{"question": "<texte libre ou lien>"}` rend `recherche.v1` **sans appeler Oriane** : `question`, `type` (`phrase` ou `lien`), `filtres` {`phrases[]`, `dans` = « parole ou texte à l'écran », `fenetre` {debut, fin}, `comptes[]`, `comptes_exclus[]`, `plateformes[]`, `identifiant_plateforme` pour un lien}, `requete_en_clair`, `cout_estime` {`credits_estimes`, `methode`} (15 par page de 100 en `default`, une page par phrase), `refus` (`null` ou {`code`, `detail`}), `mode`, `enregistre_le`.
2. `POST /v1/recherches` même corps : prépare, puis, sans `refus`, exécute `rechercher()` (une page) ; écrit les vidéos en base ; type `phrase` : calcule un récit `recit.v1` pour la phrase (règle S05) et l'ajoute au radar (`GET /v1/radar` le sert ensuite, `calcule_le` mis à jour) ; type `lien` : rend la vidéo `video.v1` trouvée par `platformId` (relevé Oriane, point 32) ; rend `{"recherche": recherche.v1, "recit": recit.v1 | null, "video": video.v1 | null}` ; 201. Journal : une entrée par appel Oriane, comme S03. En mode `enregistre` : type `phrase`, si une phrase du cas correspond (normalisation `mots.v1`), rend son récit sans appel ; sinon 409 `recherche_indisponible` « Mode enregistré : seules les phrases du cas sont servies » ; type `lien`, vidéo du cas si l'identifiant correspond, sinon 404 `introuvable`.

Traduction déterministe (aucun modèle de langue ; H à confirmer par l'usage) : phrase entre guillemets « » ou "" → phrase exacte ; sans guillemets, la question débarrassée des expressions de temps et d'exclusion devient la phrase exacte ; « depuis hier », « 24 h », « 48 h », « 7 jours », « depuis N jours » → `fenetre` (défaut 7 jours) ; « hors comptes de partis » → `comptes_exclus` lus dans un fichier de configuration `CHEMIN_COMPTES` (format `{"partis": [...], ...}`, hors Git, vide par défaut) ; « sur tiktok », « instagram », « youtube » → `plateformes` ; un lien `tiktok.com`, `instagram.com`, `youtube.com` ou `youtu.be` → type `lien` avec `identifiant_plateforme` extrait. **RG-02** : une phrase de un à trois mots tous en capitale initiale et sans chiffre est refusée (`refus.code` = `nom_seul`, `detail` = « Une recherche sur le seul nom d'une personne est refusée : cherche une phrase, une image ou un thème. ») ; une question vide → 422 `validation`.

## Fichiers réservés

`app/recherche.py` (traduction, préparation, exécution), `app/routes/recherches.py` (deux routes, branchées dans `app/main.py` : une ligne), `app/modeles.py` (classes `FiltresRecherche`, `CoutEstime`, `RefusRecherche`, `Recherche`, `ResultatRecherche`, constante `RECHERCHE_V1`), `app/config.py` (`CHEMIN_COMPTES`), `app/liste_blanche.py` (si le filtre `platformId` manque : l'ajouter à la table, un commentaire), `contrats/recherche.v1.schema.json` (export), `contrats/api.v1.json` (réexport), `tests/test_recherche.py`, `tests/test_contrats.py` (`ROUTES_IMPLEMENTEES` et schéma), `tests/test_regles_transverses.py` (deux routes couvertes : mode partout, clé de démo, aucun libellé refusé), `scripts/verifier_parcours.py` (un geste « je cherche » ajouté, phrase du cas), `.env.example` (`CHEMIN_COMPTES`), `01_Docs/05_Integration/branchement-lovable-et-oriane.md` § 2 (ligne « Je cherche »). Rien dans `app/ecart.py`, `app/fiche.py`, `app/resume.py`.

## Règles de confiance (testées)

Aucun appel Oriane dans `preparer` ; les filtres affichés sont ceux envoyés (le corps construit par `rechercher` dérive des mêmes valeurs) ; aucun nom de champ Oriane dans `recherche.v1` ; `mode` partout ; RG-02 testée sur « Jean Dupont » et « Marie », acceptée sur « places de crèche en 2027 » et « Dupont annonce 300 places » ; coût estimé égal au coût journalisé après exécution simulée ; `X-Cle-Demo` exigé sur les deux POST.

## État du poste

Poste principal sans Python : vérification par le workflow GitHub ; poste secondaire : Python 3.12 dans `C:\Users\User\AppData\Local\Programs\Python\Python312`, venv `C:\Users\User\AppData\Local\Temp\claude\venv-f011`. Simulations Oriane dans `tests/conftest.py` (réutiliser `reponse_oriane_simulee`).

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
gh run list --branch feat/service-recherche --limit 1   # completed success
curl -s -X POST localhost:8080/v1/recherches/preparer -H "Content-Type: application/json" -H "X-Cle-Demo: <clé>" -d "{\"question\":\"Que dit-on depuis hier sur « places de crèche en 2027 », hors comptes de partis ?\"}"   # filtres, requete_en_clair, cout_estime 15 crédits, refus null
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; run ; écarts ; exemples JSON à transmettre au kit (une préparation, une recherche exécutée, un refus RG-02).

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | réalisateur sonnet / high | **sha** ad67937b0277fe509ca1b2bdf5022918d4345213 (merge de main 56f15b2 inclus). **Diff** vs origin/main : 16 fichiers, +2161 -15 (app/recherche.py, app/routes/recherches.py, modeles, config, oriane, liste_blanche, contrats, tests, guide § 2, verifier_parcours). **Run** GitHub 42381367288 completed success ; 393 tests passés, 1 sauté, ruff vert, exporter_contrats --verifier à 0. **Écarts** hors réserve : app/oriane.py (construire_corps et rechercher gagnent comptes_exclus et identifiants_plateforme, nécessaires aux filtres envoyés et au lien), tests/test_exemples_ecrans.py (exemption provisoire des deux réponses de S13 jusqu'aux exemples de S14, à retirer par F017) ; choix non prévus : refus supplémentaires plusieurs_phrases, phrase_trop_longue, aucune_phrase, lien_non_reconnu ; POST /v1/recherches refusée rend 422 validation avec le libellé, preparer rend 200 avec refus ; bascules (plafond, 402, deux pannes) comme l'actualisation du radar ; fusion des requetes_trouvees d'une recherche à l'autre ; verifier_parcours ne lance la recherche en direct qu'avec --lancer-la-recherche. **Points ouverts** : le filtre profileHandle.exactMatch de oriane.py est une liste, la spécification attend {values, operator} (non touché) ; RG-02 refuse aussi un sigle ou « La France ». **Exemples JSON** : dans le compte rendu rendu à l'orchestrateur. |
