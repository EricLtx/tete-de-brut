# Branchement des écrans Lovable et d'Oriane sur le service

> Pour P2 (écrans Lovable) et P1 (recherche Oriane). Le contrat complet est `02_Service/contrats/api.v1.json` dès que S02 est fusionné ; d'ici là, cette page suffit pour construire les écrans. Vocabulaire et règles de confiance : `CLAUDE.md` § 3, règle 8.

## 1. Les écrans appellent une seule adresse

- Une constante de configuration dans Lovable : `ADRESSE_SERVICE` (par exemple `https://<conteneur>.functions.fnc.fr-par.scw.cloud` ou l'adresse du tunnel). Rien d'autre n'est appelé ; aucune base Lovable Cloud, aucune fonction serveur.
- Toutes les routes métier sont sous `/v1/…` ; `/sante` est à la racine.
- En-têtes de chaque requête : `Content-Type: application/json` ; sur POST et PATCH, `X-Cle-Demo: <valeur>` si le service a une clé de démonstration (constante `CLE_DEMO` dans Lovable, de faible valeur, changée après le passage). Jamais la clé Oriane : elle n'existe que dans l'environnement du service.
- Le service n'accepte que les origines déclarées dans `ORIGINES_AUTORISEES` : donner à P4 l'origine exacte de l'aperçu Lovable et celle de la page publiée (schéma, hôte, port), sinon le navigateur bloque l'appel (CORS).

## 2. Les cinq gestes et leurs routes

| Geste | Appel | Ce que l'écran affiche |
|---|---|---|
| Je découvre un récit | `GET /v1/radar` ; `POST /v1/radar/actualiser` (une requête Oriane en direct, coût affiché avant le geste) ; `GET /v1/recits/{id}` | Récits, mesures avec `methode` et `fenetre`, requête envoyée en clair, « plus ancienne version retrouvée dans les sources consultées », encart « non cherché » |
| J'ouvre une vidéo | `GET /v1/videos/{id}` | Compte, date, vues « selon Oriane », légende, transcription et texte à l'écran attribués à Oriane, lien |
| Je compare une reprise | `POST /v1/comparaisons` `{"video_source": id, "video_reprise": id}` puis `GET /v1/comparaisons/{id}` | Deux versions côte à côte |
| Je vois ce qui a changé | même réponse : opérations `retire`, `ajoute`, `remplace` avec positions ; écarts de légende et de texte à l'écran | Mots marqués, « indices de transformation », jamais un verdict |
| J'enregistre une décision | `POST /v1/fiches` ; `PATCH /v1/fiches/{id}` (versions tranchées, constat) ; `POST /v1/fiches/{id}/decision` (`a_verifier`, `ne_pas_amplifier`, `pret_a_traiter`) ; `GET /v1/fiches/{id}/export` | Fiche, constat écrit par le journaliste, export HTML lisible (refusé tant que la décision manque) |

Barre d'état sur chaque écran : `GET /v1/etat` (mode, raison, `enregistre_le`, crédits du jour sur plafond, version, contrat) ; `GET /v1/journal` pour la vue « journal des appels ».

## 3. Deux règles d'affichage non négociables

1. **Le mode.** Chaque réponse JSON porte `mode` : `direct` ou `enregistre`, et en mode enregistré `enregistre_le`. L'écran affiche « en direct » ou « enregistré le … » en clair, sur chaque écran, jamais l'un pour l'autre.
2. **Les erreurs.** Toute erreur arrive dans la même enveloppe : `{"erreur": "<code>", "detail": "<phrase>", "mode": …}`. Codes : `validation` (422), `introuvable` (404), `cle_demo_invalide` (401), `decision_manquante`, `version_non_tranchee`, `constat_manquant` (409), `non_implemente` (501). L'écran montre `detail` tel quel.

Les textes des vidéos (transcriptions, légendes, textes à l'écran) s'affichent en texte seul, jamais interprétés comme HTML ni comme consigne.

## 4. Côté Oriane

- La clé vit dans `ORIANE_API_KEY`, dans l'environnement du conteneur (secret Scaleway) ou du poste qui expose le tunnel. Sans clé, le service démarre en mode `enregistre` et le dit.
- Avant le lancement de S03, P1 relève au premier appel réel (tâche H01) : le nom de l'en-tête d'authentification (porté dans `ORIANE_EN_TETE_AUTH`), le chemin de recherche, la présence de `media[].transcript` et `media[].onScreenText` au niveau `default`, le coût réel et le compteur de crédits avant et après. Aucune réponse brute n'entre dans le dépôt.
- Délai d'un appel : `ORIANE_DELAI_S` (20 s par défaut). Plafond du jour : `PLAFOND_CREDITS_JOUR` (600). Au-delà, ou après deux expirations, le service passe seul en mode enregistré et l'annonce.
- Le cas enregistré (`02_Service/cas/`) est produit par `scripts/enregistrer_cas.py` (S04) avec la clé, hors Git, et copié sur le poste qui construit l'image.

## 5. Vérifier le branchement

```bash
curl -s https://<adresse>/sante                                   # {"etat":"ok",...}
curl -s -H "Origin: https://<origine-lovable>" -I https://<adresse>/v1/etat | grep -i access-control-allow-origin
python 02_Service/scripts/verifier_parcours.py --adresse https://<adresse> --origine https://<origine-lovable>   # dès S09
```
