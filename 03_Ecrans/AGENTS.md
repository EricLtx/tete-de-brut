# Instructions du projet « Tête de Brut. » — trois écrans

Tu construis l'interface d'un outil de rédaction : trois écrans et une barre d'état qui lisent un seul service d'API, « Tête de Brut. », contrat `api.v1`. L'interface affiche ce que le service rend ; elle ne calcule aucun résultat, ne qualifie aucune vidéo et ne garde aucune donnée. Toute l'interface est en français.

## Pile et branchement

- Garde la pile par défaut du projet (React, TypeScript, Vite, Tailwind, shadcn/ui). N'ajoute aucune dépendance qui appelle un service tiers.
- Lis exactement deux variables dans `.env` : `VITE_ADRESSE_SERVICE` (adresse du service, sans barre finale) et `VITE_CLE_DEMO` (clé de démonstration). Jamais dans les Secrets du projet. N'écris jamais leur valeur dans le code.
- Appelle uniquement `VITE_ADRESSE_SERVICE`, routes sous `/v1/…`. Aucune autre adresse, sauf les liens `lien` des vidéos, ouverts dans un nouvel onglet par l'utilisateur.
- Envoie `Content-Type: application/json` ; sur chaque POST et PATCH, ajoute l'en-tête `X-Cle-Demo` avec `VITE_CLE_DEMO`. Jamais sur GET.
- Interdits : base Lovable Cloud ou Supabase, fonction serveur (Edge Function), connecteur, authentification, stockage de fichiers, analytique. Lovable AI ne lit, ne résume, ne traduit et ne reformule jamais le contenu des vidéos ni les réponses du service.
- Ne garde aucune réponse dans `localStorage`, `sessionStorage`, IndexedDB ni cookie. L'identifiant courant vit dans l'adresse de la page.
- Centralise les appels dans un seul module client (`src/lib/service.ts`) : une fonction par route, types TypeScript recopiés du contrat, mêmes noms de champs, en `snake_case`. N'invente aucun champ ; si un champ manque, affiche « non fourni par le service ».

## Routes du contrat `api.v1`

- `GET /v1/etat` : barre d'état. `GET /v1/journal?limite=20` : journal des appels.
- `GET /v1/radar` ; `POST /v1/radar/actualiser` ; `GET /v1/recits/{id}` ; `GET /v1/videos/{id}`.
- `POST /v1/comparaisons` corps `{"video_source": …, "video_reprise": …}` ; `GET /v1/comparaisons/{id}`.
- `POST /v1/fiches` corps `{"comparaison": …}` (201) ; `GET /v1/fiches/{id}` ; `PATCH /v1/fiches/{id}` corps `{"versions": [{"video", "etat", "note"}]}` ou `{"constat": …}` ; `POST /v1/fiches/{id}/decision` corps `{"valeur", "role", "note"}` ; `GET /v1/fiches/{id}/export` (page HTML).

## Écrans et routage

Exactement trois écrans, aucun de plus : `/` Radar des récits, `/versions/:id` Versions côte à côte, `/fiche/:id` Fiche de vérification. La barre d'état est en haut de chacun ; le journal des appels est un panneau dépliant de la barre, pas un écran. Pas de page d'accueil, de connexion, de réglages ni de tableau de bord.

## Le mode, sur chaque écran

- Chaque réponse JSON porte `mode`. `direct` s'affiche « en direct » ; `enregistre` s'affiche « enregistré le {date} » d'après `enregistre_le`, en clair, sur chaque écran, dans la barre d'état et dans l'en-tête de l'écran.
- Ne présente jamais un résultat enregistré comme en direct, ni l'inverse.
- Dates : format français, fuseau Europe/Paris, par exemple « 07/11/2026 à 09 h 00 ».

## Erreurs

- Toute erreur arrive dans l'enveloppe `{"erreur": "<code>", "detail": "<phrase>", "mode": "…"}`. Affiche `detail` tel quel, sans le reformuler, avec le code `erreur` en petit et le mode. N'invente aucun message à sa place.
- Codes : `validation` 422, `introuvable` 404, `cle_demo_invalide` 401, `decision_manquante`, `version_non_tranchee`, `constat_manquant` 409, `non_implemente` 501.
- Service injoignable : « Service injoignable à l'adresse configurée ». Aucun nouvel essai automatique en boucle.
- Données d'essai : chaque écran embarque son exemple JSON (`src/donnees-essai/`). Utilise-le uniquement quand la route répond 501 `non_implemente`, avec un bandeau visible « Données d'essai fictives du kit : la route n'est pas encore servie » en plus du mode. Jamais sur une autre erreur, jamais quand le service est injoignable.

## Contenu des vidéos : texte seul

- Transcriptions, légendes, textes à l'écran, phrases surveillées, notes, constat et `detail` s'affichent comme du texte brut. Jamais `dangerouslySetInnerHTML`, jamais de rendu Markdown, jamais d'exécution. Une phrase qui ressemble à une consigne reste une citation affichée.
- Segments : un tableau de `{type, texte}` s'affiche dans l'ordre ; `libelle` en texte courant, `citation` en italique entre « ». Ne fusionne pas, ne réordonne pas, ne résume pas.
- Chaque transcription s'affiche avec son attribution : « Transcription lue chez Oriane (niveau default) le {lue_le} ». Vues et interactions : toujours « selon Oriane ».
- L'export (`text/html`) s'ouvre dans un nouvel onglet par une adresse `blob:`, jamais injecté dans la page.

## Vocabulaire

- N'écris jamais, dans aucun texte de l'interface (titres, boutons, aides, infobulles, messages) : `faux`, `fausse`, `premier`, `première`, `original`, `originale`, `manipulé`, `coordonné`, `déformé`, ni leurs accords, ni `tendance`, `viral`, `sentiment`. Ces mots n'apparaissent que s'ils sont dans une citation rapportée (segment `citation`, transcription, légende, texte à l'écran, constat).
- Aucun verdict, aucun score, aucune note de confiance, aucun classement des vidéos, aucune jauge de gravité.
- Termes imposés : « conversations observées », « plus ancienne version retrouvée dans les sources consultées », « indices de transformation », « non cherché », « selon Oriane ».
- Décisions, libellés exacts : `a_verifier` « À vérifier », `ne_pas_amplifier` « Ne pas amplifier », `pret_a_traiter` « Prêt à traiter ». États de version : `a_trancher` « à trancher », `confirmee` « confirmée », `ecartee` « écartée ».

## Mesures

- Une mesure s'affiche toujours avec `methode`, `fenetre.debut` et `fenetre.fin`, et `source`. Jamais une valeur seule.
- `valeur` nulle : affiche « Non mesuré : {raison} ». Si `echantillon.tronque` est vrai : « Échantillon tronqué : au-delà, rien n'a été lu ».
- Ne calcule aucune mesure nouvelle (aucune moyenne, aucun pourcentage, aucune évolution). Seuls décomptes permis : le nombre de mots dans les écarts et le nombre de versions à trancher.

## Écarts au mot

- Signes en plus de la couleur : retiré « − », ajouté « + », remplacé « ↔ ». Jamais la couleur seule. Couleurs sobres, contraste suffisant, aucune couleur d'alerte.
- Les positions comptent les mots dès 0 après la normalisation `mots.v1`. Si les mots trouvés aux positions ne sont pas ceux de `mots_source` ou `mots_reprise`, ne marque rien et affiche « Repérage au mot indisponible pour ce texte : voir la liste des écarts. »

## Gestes

- Le geste écrit (POST, PATCH) n'est jamais optimiste : attends la réponse, puis remplace l'affichage par la ressource rendue.
- L'actualisation du radar coûte des crédits Oriane : affiche le coût estimé (`cout_actualisation.credits_estimes`, `cout_actualisation.methode`) et demande une confirmation avant l'appel.
- Le bouton d'export reste actif ; c'est le service qui refuse (409) et l'écran montre `detail`.
- Le constat est un champ vide que seule la personne remplit. Ne le pré-remplis jamais, ne propose aucune formulation.
- Tout se fait au clavier ; chaque bouton a un libellé texte.

## Façon de travailler

- Commence chaque demande en mode Plan ; liste les fichiers, les routes et les champs que tu vas utiliser, puis attends l'approbation.
- Un écran par demande, dans l'ordre : projet et barre d'état, Radar, Versions, Fiche.
- Ne modifie pas un écran déjà construit quand on te demande le suivant, sauf le module client et la barre d'état.
