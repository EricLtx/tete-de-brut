---
mandat: F020
titre: S17 — Recherche : couverture maximale (noyaux de mots en ordre libre par `includesFuzzy`, variantes multiples) et un seul récit par recherche
statut: no-go
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S17
branche: feat/service-recherche-couverture (part de main)
worktree: .claude/worktrees/feat-service-recherche-couverture
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T16:40Z
rendu_a: 2026-11-07T17:00Z
go_a:
allers_retours: 1
---

# F020 — S17, couverture de la recherche et un récit par recherche

## Constat de l'équipe (07/11, 17 h 15, sur le service réel)

La question « perdre du pouvoir d'achat » a bien été reformulée par le modèle (journal `recherche.reformulation`, entrée 25) en trois phrases exactes : « le pouvoir d'achat », « pouvoir d'achat en baisse », « perdre du pouvoir d'achat ». Oriane a rendu 123 vidéos pour la première et 0 pour les deux autres. Le service a alors créé **trois récits**, dont deux vides, et le radar montre « perdre du pouvoir d'achat · 0 vidéos » : le journaliste conclut que la recherche n'apporte rien alors que 123 vidéos sont rangées sous « le pouvoir d'achat ». Deux causes :

1. **Un récit par phrase** (choix de S15) au lieu d'un récit par recherche : la couverture est éclatée et les variantes sans résultat polluent le radar.
2. **Phrase exacte seulement** (`includesExactly`) : « le pouvoir d'achat » ne retrouve ni « du pouvoir d'achat », ni « mon pouvoir d'achat », ni « pouvoir d'achat en baisse ». La spécification OpenAPI d'Oriane (`veille/sources/oriane-integration-connect.openapi.json` du dépôt privé, `SearchContentsRequest.Filters.Body`, champs `transcript`, `onScreenText`, `caption`) offre `includesFuzzy` : « Requires matches of all words in any order, including partial words, inside the field ». C'est l'opérateur de couverture : « pouvoir achat » retrouve toutes ces formes, « retraite » retrouve « retraites ».

À part : la question « glucksman » (minuscules) est passée (15 vidéos) malgré RG-02, parce que `est_nom_seul` ne regarde que la capitale initiale et que le modèle n'a pas rendu de liste vide.

Le mandat renvoie à `app/recherche_modele.py` (consigne, schéma `Reformulation`, `MAX_PHRASES`, `MOTS_MIN`), `app/recherche.py` (`preparer`, `executer`, `_recit_le_plus_fourni`, document `recherche-…`, écriture des `requetes_trouvees`), `app/recits.py` (`phrases_surveillees`, `videos_du_recit`, `construire_recit`, `supprimer_recit`), `app/oriane.py` (sous-requêtes nommées `dit:`/`ecrit:` en `or`), `app/liste_blanche.py` (opérateurs), aux contrats et aux tests ; il ne les recopie pas.

## Objectif

1. **Reformulation pour la couverture.** Le modèle rend désormais, pour une question libre : `noyaux` (un à trois groupes de deux à trois mots pleins, sans article ni mot vide, dans l'ordre naturel, qui nomment le sujet tel qu'on le dit le plus souvent : « pouvoir achat », « prix essence », « réforme retraites »), `phrases` (zéro à cinq phrases exactes de deux à six mots, formulations courantes et synonymes : « fin du mois difficile », « tout augmente », « prix du carburant »), `personne_seule` (booléen : la question ne porte que sur le nom d'une personne), plus `jours`, `exclusions`, `plateformes` comme aujourd'hui. Consigne : couvrir le sujet au maximum, du plus général (noyau) au plus précis (phrase) ; aucun mot de temps ; rien d'inventé hors de la question et de ses synonymes évidents. Schéma pydantic bornant chaque élément (longueur, nombre de mots, 256 caractères), déduplication, RG-02 sur chaque élément, `personne_seule` vrai → refus 422 RG-02 (même libellé que `est_nom_seul`), sans appel à Oriane. Repli déterministe quand le modèle est absent ou en échec : un noyau = mots pleins de la question (liste de mots vides courante en français dans le code, au plus trois mots gardés dans l'ordre), et la phrase entre guillemets si la question en contient une. Une phrase entre guillemets reste une phrase exacte, jamais un noyau.
2. **Requête Oriane.** Une page, sous-requête `or` comme aujourd'hui : chaque noyau donne deux sous-requêtes nommées `mots:<noyau>` sur `transcript` et `onScreenText` avec `includesFuzzy: {"values": ["<noyau>"], "operator": "or"}` ; chaque phrase exacte garde `dit:`/`ecrit:` en `includesExactly`. `app/liste_blanche.py` déclare `OPERATEUR_MOTS = "includesFuzzy"` avec la citation de la spécification ; les filtres affichés par `recherche.v1` (`filtres`) sont ceux envoyés. Coût estimé inchangé (une requête).
3. **Un récit par recherche.** Le document `recherche-…` porte `pivot` (le premier noyau, sinon la première phrase, sinon la question nettoyée ; c'est la `phrase_surveillee` du récit) et `variantes` (tous les noyaux et phrases, dans l'ordre). `recits.phrases_surveillees` traite un tel document comme **une seule** entrée, de clé `cle_phrase(pivot)`, dont les vidéos sont celles qui ont au moins une variante dans `requetes_trouvees` (`videos_du_recit` reçoit l'ensemble des clés) ; une vidéo trouvée par deux variantes compte une fois. `recit.v1` gagne un champ optionnel `variantes: list[str]` ; `requete_en_clair` les énumère (« reformulée par un modèle de langue : mots « pouvoir achat » en tout ordre ; phrases exactes « … », « … » »). `POST /v1/recherches` rend ce récit unique (`_recit_le_plus_fourni` disparaît) ; `GET /v1/radar` montre une carte par recherche, même vide (le journaliste voit sa recherche et ses variantes) ; `DELETE /v1/recits/{id}` d'un récit à variantes retire toutes ses variantes des `requetes_trouvees` et le document de recherche (F019 généralisé). Si le pivot est déjà une phrase du cas (« le pouvoir d'achat » vs « pouvoir achat » sont deux clés : pas de fusion forcée), les deux récits coexistent ; si les clés sont égales, l'entrée du cas garde la priorité et gagne les variantes. Mode enregistré : même règle de regroupement sur le cas rejoué.
4. **Écrans.** Aucun changement exigé côté Lovable (l'écran lit `phrase_surveillee`, `requete_en_clair`, `phrases` de `recherche.v1`) ; `recherche.v1.phrases` liste toutes les variantes (noyaux puis phrases) pour que l'écran « Ta question devient N filtres » reste vrai.

## Fichiers réservés

`app/recherche_modele.py`, `app/recherche.py`, `app/recits.py`, `app/oriane.py` (construction des sous-requêtes seulement), `app/liste_blanche.py`, `app/modeles.py` (`Recit.variantes` optionnel ; `Recherche` si un champ transite), `contrats/recit.v1.schema.json`, `contrats/recherche.v1.schema.json`, `contrats/api.v1.json` (réexport), `tests/test_recherche.py`, `tests/test_radar.py`, `tests/conftest.py`, `03_Ecrans/exemples/recit.json` et `03_Ecrans/exemples/radar.json` seulement si le test du kit l'exige. Rien dans `app/fiche.py`, `app/ecart.py`, `app/routes/` sauf si un champ doit transiter.

## Règles de confiance (testées)

Aucun appel au modèle sans clé ni en mode `deterministe` ; seule la question part au modèle ; aucun sujet inventé ; les filtres affichés sont ceux envoyés ; RG-02 sur chaque noyau et chaque phrase, et `personne_seule` refusé ; une recherche = un récit ; une vidéo trouvée par deux variantes comptée une fois ; journal de la recherche et de la reformulation ; `mode` partout ; aucun secret dans les journaux ni dans le dépôt.

## État du poste

Python 3.12 dans `C:\Users\User\AppData\Local\Programs\Python\Python312` (hors PATH), venv `C:\Users\User\AppData\Local\Temp\claude\venv-f011`. Clés hors Git dans `C:\Users\User\.tete-de-brut\oriane.env` et `claude.env` : à charger dans l'environnement du shell pour les tests `reel` (`set -a; source …; set +a`), jamais lues ni affichées autrement. Les tests `reel` coûtent 15 crédits Oriane par recherche : deux au plus.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
set -a; source ~/.tete-de-brut/oriane.env; source ~/.tete-de-brut/claude.env; set +a; python -m pytest -q -m reel tests/test_recherche.py   # vert : « perdre du pouvoir d'achat » → un seul récit, noyau « pouvoir achat », au moins 100 vidéos
gh run list --branch feat/service-recherche-couverture --limit 1   # completed success
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; tests (dont `reel`) ; écarts ; exemple obtenu (question → noyaux, phrases, nombre de vidéos par variante et au total) et forme exacte de la sous-requête `includesFuzzy` envoyée.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-09 | orchestrateur | Branche raccordée à `main` (55992e7, 597 tests, run `pipeline` vert). Doublage `vault/revues/F020-55992e7.md` : NO-GO, 1 bloquant (run `reel` 42534842980 : 68 vidéos pour 100 exigées), 1 majeur (noyaux aussi envoyés en phrase exacte, acté au plan le 09/11), 4 mineurs. |
| 2026-11-09 | orchestrateur | **F020b**, correctif sur la même branche, `sonnet` / low. (1) Critère de fin révisé : le seuil absolu de 100 vidéos sur données vivantes est remplacé par un invariant relatif. Sur la même fenêtre, le récit unique couvre au moins autant de vidéos que la phrase exacte « pouvoir d'achat » seule, et au moins autant que chacune de ses variantes. Le test `reel` le vérifie en une seule exécution, avec au plus une sous-requête de plus. (2) Test hors réseau qui envoie deux noyaux de bout en bout : la mutation `noyaux=filtres.noyaux[:1]` doit le faire échouer (constat 4). Réserve : `tests/test_recherche.py`, et `app/recherche.py` seulement si la comparaison l'exige. Fin : ruff, pytest hors `reel` et run `pipeline` verts, puis `gh workflow run reel.yml --ref feat/service-recherche-couverture` vert, deux lancements au plus (15 à 45 crédits Oriane chacun). Relu sur le seul diff entre 55992e7 et le nouveau sha. |
| 2026-11-09 | orchestrateur | F020b rendu b974792 (test relatif et test à deux noyaux, `pipeline` vert ; mutation `noyaux[:1]` attrapée). Run `reel` 42536089047 : l'invariant échoue, avec 68 vidéos au récit contre au moins 100 pour la phrase exacte seule (page pleine), 66 pour la meilleure variante dans la requête combinée, et 0 pour le noyau flou « perte pouvoir d'achat ». La recherche combinée couvre moins que la phrase seule : défaut de code. |
| 2026-11-09 | orchestrateur | **F020c**, même réalisateur, `sonnet`. Trouver pourquoi la requête combinée n'est pas un sur-ensemble de chaque sous-requête (construction du corps Oriane, opérateurs, pagination ou plafond d'une page, tri, `matchedQueries` vers `requetes_trouvees`, écartées), puis corriger pour que l'invariant relatif du test `reel` tienne. Budget réel : six appels Oriane au plus en local (90 crédits), et un lancement `reel` sur GitHub. Réserve : celle du mandat. Ne pas affaiblir le test. |

