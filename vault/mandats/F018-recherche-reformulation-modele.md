---
mandat: F018
titre: S15 — Recherche : reformulation de la question par le modèle de langue (phrases exactes, fenêtre, exclusions), fenêtre par défaut élargie, lien collé vérifié en réel
statut: fusionne
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S15
branche: feat/service-recherche-modele (part de origin/feat/service-recherche)
worktree: .claude/worktrees/feat-service-recherche-modele
modele: sonnet
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T15:25Z
rendu_a: 2026-11-07T15:45Z
go_a: 2026-11-07T15:55Z
allers_retours: 0
---

# F018 — S15, reformulation de la recherche par le modèle de langue

Constat de l'équipe le 07/11 à 16 h 20, sur le service réel : une question libre (« Donne moi les informations récentes sur la réforme des retraites ») est prise entière comme phrase exacte et ne rend rien ; la fenêtre par défaut de sept jours tombe dans une période vide de l'index Oriane (les vidéos trouvées datent du début octobre 2026). Décision : la question est reformulée par le modèle de langue (ADR-0002, clé déjà prévue par S10) en phrases exactes courtes, la fenêtre par défaut passe à 30 jours, et le lien collé est vérifié en réel. Le mandat renvoie à `app/recherche.py`, `app/routes/recherches.py`, `app/config.py` (configuration du modèle : `modele_langue_url`, `modele_langue_cle`, `modele_langue_id`, voir les noms d'environnement dans `config.py` et `.env.example`), `app/oriane.py` et aux tests existants ; il ne les recopie pas.

## Objectif

1. **Reformulation** dans `preparer` : quand la clé du modèle est présente et que `RECHERCHE_MODE` vaut `modele` (valeur par défaut quand la clé est présente ; `deterministe` sinon ou sur demande), la question libre est envoyée au modèle (API Messages d'Anthropic par `httpx`, adresse et identifiant de modèle lus dans la configuration, température 0, réponse JSON seule, délai 8 s) avec une consigne en français qui demande : `phrases` (une à trois phrases exactes de trois à six mots, telles qu'elles seraient prononcées ou écrites à l'écran dans une vidéo, en minuscules sauf noms propres, jamais un nom de personne seul), `jours` (fenêtre en jours si la question l'exprime, sinon null), `exclusions` (catégories de comptes à exclure, par exemple « partis »), `plateformes` (parmi tiktok, instagram, youtube). Le JSON est validé par un modèle pydantic ; toute erreur, expiration ou JSON invalide → repli sur la traduction déterministe existante, journalisé. Une phrase entre guillemets dans la question n'est jamais reformulée. RG-02 (`est_nom_seul`) s'applique à chaque phrase rendue. `requete_en_clair` commence par « reformulée par un modèle de langue : » puis la requête en clair habituelle. Le mode utilisé (`modele` ou `deterministe`) figure dans `recherche.v1` par un champ optionnel `reformulation` (`"modele"`, `"deterministe"`, `null`).
2. **Fenêtre par défaut** : `JOURS_PAR_DEFAUT` passe à 30 jours (déterministe et modèle) ; « depuis hier », « 7 jours », « depuis N jours » restent honorés.
3. **Exécution** : `POST /v1/recherches` cherche les phrases rendues (une page, sous-requête `or` comme S03) et calcule un récit par phrase (règle S05) ; `recit` dans la réponse est le récit qui a le plus de vidéos ; les récits sans vidéo sont tout de même ajoutés au radar.
4. **Lien collé, en réel** : avec la clé Oriane, un test marqué `reel` prépare puis exécute une recherche sur un lien TikTok et un lien Instagram de vidéos présentes dans l'index (prendre `lien` de deux vidéos rendues par `GET /v1/radar` du cas enregistré) et vérifie que `video` est rendue ; si le filtre `platformId` de `rechercher` ne rend rien, corriger le corps de la requête d'après la spécification OpenAPI d'Oriane (relevé H01 : `platformId` et `audioPlatformId` sont des couples plateforme et identifiant) et consigner la forme exacte dans `app/liste_blanche.py`.

## Fichiers réservés

`app/recherche.py` (reformulation, repli, fenêtre, exécution multi-phrases), `app/recherche_modele.py` (nouveau : appel du modèle, consigne, validation), `app/modeles.py` (champ optionnel `reformulation` de `Recherche`), `app/config.py` (`RECHERCHE_MODE`), `.env.example` (`RECHERCHE_MODE`), `app/oriane.py` et `app/liste_blanche.py` (seulement si le filtre de lien doit être corrigé), `contrats/recherche.v1.schema.json` et `contrats/api.v1.json` (réexport), `tests/test_recherche.py` (modèle simulé par `MockTransport` : reformulation acceptée, JSON invalide → repli, expiration → repli, guillemets respectés, RG-02 après reformulation, fenêtre 30 jours ; test `reel` du lien collé), `tests/conftest.py` (fixture de réponse du modèle). Rien dans `app/fiche.py`, `app/ecart.py`, `app/routes/` hors `recherches.py` si un champ doit transiter.

## Règles de confiance (testées)

Aucun appel au modèle sans clé ni en mode `deterministe` ; le contenu des vidéos n'est jamais envoyé au modèle (seule la question du journaliste) ; aucune phrase inventée hors de la réponse du modèle ou de la question ; `requete_en_clair` dit la reformulation ; aucun secret dans le dépôt ni dans les journaux (clé masquée) ; `mode` partout ; les filtres affichés sont ceux envoyés.

## État du poste

Python 3.12 dans `C:\Users\User\AppData\Local\Programs\Python\Python312` (hors PATH), venv `C:\Users\User\AppData\Local\Temp\claude\venv-f011`. Clés hors Git dans `C:\Users\User\.tete-de-brut\oriane.env` et `claude.env` : à charger dans l'environnement du shell pour les tests `reel` (`set -a; source …; set +a`), jamais lues ni affichées autrement. L'identifiant de modèle par défaut est `claude-sonnet-5-5` (configuration) ; `claude-haiku-5-5` est acceptable pour la vitesse si le temps de réponse dépasse 4 s.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert
set -a; source ~/.tete-de-brut/oriane.env; source ~/.tete-de-brut/claude.env; set +a; python -m pytest -q -m reel tests/test_recherche.py   # vert : reformulation réelle et lien collé
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; tests (dont `reel`) ; écarts ; forme exacte du filtre de lien et exemple de reformulation obtenue (question → phrases, fenêtre).

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | réalisateur (sonnet / high) | Rendu 5993112 sur feat/service-recherche-modele : reformulation par le modèle (sonnet-5-5, output_config.effort low, pas de temperature), repli déterministe, cache 5 min, fil dédié ; tests 498 verts, deux tests reel verts (question libre → « la réforme des retraites », « réforme des retraites », 71 et 90 vidéos ; liens TikTok et Instagram rendus) ; filtre de lien existant confirmé ; run GitHub vert. Écarts : coût estimé 15 quel que soit le nombre de phrases ; règles de tri des phrases ; précédence de la question sur le modèle. |
| 2026-11-07 | orchestrateur | Rendu vérifié par le run GitHub vert et déployé dans le Codespace de démonstration (branche demo/enregistrement) ; doublage lancé. |
| 2026-11-07 | orchestrateur | Doublage GO (`vault/revues/F018-5993112.md`, quatre mineurs : repli gardé 5 min, éviction du cache sans verrou, exclusions non bornées, délai global non testé) ; fusion 3244076 dans `main` ; branche et worktree retirés. Constaté sur le service de démonstration : question sur le prix de l'essence reformulée en trois phrases, 65 vidéos ; lien TikTok collé rendu. |
