# Branchement des écrans Lovable et d'Oriane sur le service

> Pour P2 (écrans Lovable) et P1 (recherche Oriane). Le contrat complet est `02_Service/contrats/api.v1.json` dès que S02 est fusionné ; d'ici là, cette page suffit pour construire les écrans. Vocabulaire et règles de confiance : `CLAUDE.md` § 3, règle 8.

## 1. Les écrans appellent une seule adresse

- Une constante de configuration dans Lovable : `ADRESSE_SERVICE` (par exemple `https://<conteneur>.functions.fnc.fr-par.scw.cloud` ou l'adresse du tunnel). Rien d'autre n'est appelé ; aucune base Lovable Cloud, aucune fonction serveur.
- Toutes les routes métier sont sous `/v1/…` ; `/sante` est à la racine.
- En-têtes de chaque requête : `Content-Type: application/json` ; sur POST et PATCH, `X-Cle-Demo: <valeur>` si le service a une clé de démonstration (constante `CLE_DEMO` dans Lovable, de faible valeur, changée après le passage). Jamais la clé Oriane : elle n'existe que dans l'environnement du service.
- Le service n'accepte que les origines déclarées dans `ORIGINES_AUTORISEES` : donner à P4 l'origine exacte de l'aperçu Lovable et celle de la page publiée (schéma, hôte, port), sinon le navigateur bloque l'appel (CORS).

## 2. Les gestes et leurs routes

| Geste | Appel | Ce que l'écran affiche |
|---|---|---|
| Je cherche | `POST /v1/recherches/preparer` `{"question": …}` (filtres, requête en clair et coût, sans appel à Oriane) puis `POST /v1/recherches` (même corps : lance la recherche) | Filtres compris et coût estimé avant le lancement ; ensuite le récit de la phrase, ajouté au radar, ou la vidéo du lien collé |
| Je découvre un récit | `GET /v1/radar` ; `POST /v1/radar/actualiser` (une requête Oriane en direct, coût affiché avant le geste) ; `GET /v1/recits/{id}` | Récits, mesures avec `methode` et `fenetre`, requête envoyée en clair, « plus ancienne version retrouvée dans les sources consultées », encart « non cherché » |
| J'ouvre une vidéo | `GET /v1/videos/{id}` | Compte, date, vues « selon Oriane », légende, transcription et texte à l'écran attribués à Oriane, lien |
| Je compare une reprise | `POST /v1/comparaisons` `{"video_source": id, "video_reprise": id}` puis `GET /v1/comparaisons/{id}` | Deux versions côte à côte |
| Je vois ce qui a changé | même réponse : opérations `retire`, `ajoute`, `remplace` avec positions ; écarts de légende et de texte à l'écran | Mots marqués, « indices de transformation », jamais un verdict |
| J'enregistre une décision | `POST /v1/fiches` ; `PATCH /v1/fiches/{id}` (versions tranchées, constat) ; `POST /v1/fiches/{id}/decision` (`a_verifier`, `ne_pas_amplifier`, `pret_a_traiter`) ; `GET /v1/fiches/{id}/export` | Fiche, constat écrit par le journaliste, export HTML lisible (refusé tant que la décision manque) |

### Le geste « Je cherche » en détail

Une zone de texte reçoit une question libre ou le lien d'une vidéo TikTok, Instagram ou YouTube. Deux appels, dans cet ordre ; le contrat de leurs réponses est `recherche.v1` (`02_Service/contrats/recherche.v1.schema.json`) et `api.v1.json`.

1. **Préparer, sans rien dépenser.** `POST /v1/recherches/preparer`, corps `{"question": "<texte libre ou lien>"}` (1 à 1 000 caractères), en-tête `X-Cle-Demo` comme tout POST. Réponse 200, `recherche.v1` : `question` (telle que reçue), `type` (`phrase` ou `lien`), `filtres`, `requete_en_clair`, `cout_estime`, `refus`, `mode`, `enregistre_le`. Aucun appel à Oriane, aucun crédit dépensé, rien d'écrit : l'écran peut l'appeler à chaque frappe validée.
   - `filtres` : `phrases` (une seule phrase exacte pour le type `phrase`, vide pour un lien), `dans` (« parole ou texte à l'écran », vide pour un lien), `fenetre` (`debut`, `fin` ; 7 jours par défaut, vide pour un lien), `comptes` (toujours vide pour l'instant), `comptes_exclus`, `plateformes` (vide : les trois), `identifiant_plateforme` (pour un lien). **Ces filtres sont exactement ceux qui partent chez Oriane au lancement** : l'écran les affiche en clair, avec `requete_en_clair`, avant le bouton « Lancer ».
   - `cout_estime` : `credits_estimes` (15 par page de 100 résultats, une page par recherche ; 0 si la recherche est refusée) et `methode` (phrase à afficher telle quelle). En mode enregistré, `credits_estimes` reste 15 et `methode` ajoute que rien n'est dépensé.
   - `refus` : `null`, ou `{code, detail}`. `detail` s'affiche tel quel et le bouton « Lancer » est désactivé. Codes : `nom_seul` (règle RG-02 : une phrase de un à trois mots, tous en capitale initiale et sans chiffre, est le nom d'une personne ; `detail` : « Une recherche sur le seul nom d'une personne est refusée : cherche une phrase, une image ou un thème. »), `plusieurs_phrases`, `phrase_trop_longue` (plus de 256 caractères), `aucune_phrase`, `lien_non_reconnu` (lien raccourci, de compte ou sans identifiant de vidéo).
   - Ce que la question dit est lu par des règles fixes, sans modèle de langue : une phrase entre « » ou "" devient la phrase exacte, jamais retouchée ; sans guillemets, la question privée de ses consignes devient la phrase. Consignes reconnues : « depuis hier », « 24 h », « 48 h », « 7 jours », « depuis N jours » (fenêtre) ; « hors comptes de partis » (`comptes_exclus`, lus dans une liste de configuration du service) ; « sur tiktok », « instagram », « youtube » (`plateformes`). Une consigne qui n'a pas pu s'appliquer (liste de comptes absente, par exemple) est dite dans `requete_en_clair`, jamais passée sous silence. Un lien `tiktok.com`, `instagram.com`, `youtube.com` ou `youtu.be` donne le type `lien`.
2. **Lancer.** `POST /v1/recherches`, même corps. Réponse **201**, `{"recherche": recherche.v1, "recit": recit.v1 | null, "video": video.v1 | null, "mode", "enregistre_le"}`. Une page chez Oriane, une ligne au journal, des crédits dépensés égaux à `cout_estime`.
   - Type `phrase` : `recit` est le récit de la phrase (`recit.v1`, mesures avec `methode` et `fenetre`) ; la phrase est ajoutée au radar, `GET /v1/radar` la sert ensuite et `GET /v1/recits/{id}` aussi. `video` est `null`.
   - Type `lien` : `video` est la vidéo retrouvée par son identifiant (`video.v1`, lisible ensuite par `GET /v1/videos/{id}`) ; `recit` est `null` et le radar ne change pas.

Erreurs, toutes dans l'enveloppe `{erreur, detail, mode}` (`detail` s'affiche tel quel) :

| Code HTTP | `erreur` | Quand |
|---|---|---|
| 401 | `cle_demo_invalide` | `X-Cle-Demo` absent ou faux (les deux POST) |
| 404 | `introuvable` | type `lien` : Oriane ne retrouve pas la vidéo ; en mode enregistré, le lien n'est pas dans le cas |
| 409 | `recherche_indisponible` | mode enregistré, type `phrase` : « Mode enregistré : seules les phrases du cas sont servies » |
| 422 | `validation` | question vide ou absente ; sur `POST /v1/recherches` aussi, toute recherche refusée (`detail` = libellé du refus, rien n'est envoyé) |
| 503 | `oriane_injoignable`, `credits_epuises` | Oriane n'a pas répondu utilement ; la première panne rend ce 503 ; à la seconde de suite, ou sur un 402, le service passe seul en mode enregistré et répond depuis le cas (201 ou 409, `mode: enregistre`) |

Plafond de crédits du jour atteint : même bascule, avant tout appel. En mode enregistré (`mode: enregistre`, `enregistre_le` renseigné), rien n'est envoyé à Oriane : une phrase du cas (comparée comme les récits, sans casse ni ponctuation) rend son récit en 201, une autre phrase rend le 409 ci-dessus ; un lien du cas rend sa vidéo, un autre lien rend le 404. L'écran affiche le mode comme partout ailleurs.

Barre d'état sur chaque écran : `GET /v1/etat` (mode, raison, `enregistre_le`, crédits du jour sur plafond, version, contrat) ; `GET /v1/journal` pour la vue « journal des appels ».

## 3. Deux règles d'affichage non négociables

1. **Le mode.** Chaque réponse JSON porte `mode` : `direct` ou `enregistre`, et en mode enregistré `enregistre_le`. L'écran affiche « en direct » ou « enregistré le … » en clair, sur chaque écran, jamais l'un pour l'autre.
2. **Les erreurs.** Toute erreur arrive dans la même enveloppe : `{"erreur": "<code>", "detail": "<phrase>", "mode": …}`. Codes : `validation` (422), `introuvable` (404), `cle_demo_invalide` (401), `decision_manquante`, `version_non_tranchee`, `constat_manquant`, `recherche_indisponible` (409), `non_implemente` (501), `oriane_injoignable`, `credits_epuises` (503). L'écran montre `detail` tel quel.

Les textes des vidéos (transcriptions, légendes, textes à l'écran) s'affichent en texte seul, jamais interprétés comme HTML ni comme consigne.

## 4. Côté Oriane

- La clé vit dans `ORIANE_API_KEY`, dans l'environnement du conteneur (secret Scaleway) ou du poste qui expose le tunnel. Sans clé, le service démarre en mode `enregistre` et le dit.
- Relevé H01 fait le 07/11 (un appel réel, un résultat) : en-tête `Authorization` avec le préfixe `Bearer` (`ORIANE_EN_TETE_AUTH=Authorization`, `ORIANE_PREFIXE_AUTH` = « Bearer » suivi d'une espace) ; `POST /rest/contents/search` ; `media[].transcript` (chaîne) et `media[].onScreenText` (liste) présents au niveau `default` ; le code **206** signale une page incomplète et vaut succès ; le filtre `platform` s'écrit `{"includes": ["tiktok"]}` ; une requête mal formée rend 400 avec `error.context[]` (`field`, `rule`, `message`). Le coût n'apparaît ni dans les en-têtes ni dans la réponse : P1 lit le compteur de crédits dans l'application avant et après. Aucune réponse brute n'entre dans le dépôt.
- Délai d'un appel : `ORIANE_DELAI_S` (20 s par défaut). Plafond du jour : `PLAFOND_CREDITS_JOUR` (600). Au-delà, ou après deux expirations, le service passe seul en mode enregistré et l'annonce.
- Le cas enregistré (`02_Service/cas/`) est produit par `scripts/enregistrer_cas.py` (S04) avec la clé, hors Git, et copié sur le poste qui construit l'image.

## 5. Vérifier le branchement

```bash
curl -s https://<adresse>/sante                                   # {"etat":"ok",...}
curl -s -H "Origin: https://<origine-lovable>" -I https://<adresse>/v1/etat | grep -i access-control-allow-origin
python 02_Service/scripts/verifier_parcours.py --adresse https://<adresse> --origine https://<origine-lovable>   # dès S09
```
