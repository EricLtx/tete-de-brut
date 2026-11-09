# Prompt 01 — Radar des récits

À coller tel quel en mode Plan, après le prompt 00. Joindre ou coller `exemples/radar.json`, `exemples/recit.json`, `exemples/video-source.json`, `exemples/video-reprise.json`, `exemples/suppression-recit.json` et `exemples/pertinence-recit.json` (données d'essai tant que les routes répondent 501).

---

Mode Plan. Construis l'écran **Radar des récits** sur la route `/radar` (la route `/` est l'écran Recherche, prompt 04). Suis `AGENTS.md`. Propose le plan (composants, appels, champs), puis attends mon approbation. Ne touche pas aux autres écrans.

**Gestes servis** : je découvre un récit ; j'ouvre une vidéo ; je compare une reprise (départ vers l'écran Versions).

**Appels** : `GET /v1/radar` au chargement ; `POST /v1/radar/actualiser` après confirmation ; `GET /v1/recits/{id}` pour le panneau d'un récit ; `GET /v1/videos/{id}` pour chaque lien source et le panneau vidéo ; `POST /v1/comparaisons` ; `DELETE /v1/recits/{id}` ; `POST /v1/recits/{id}/pertinence`.

**En-tête** : titre « Radar des récits » ; badge de mode ; « Calculé le {calcule_le} » ; « Pourquoi : {raison} » si `raison` est présent.

**Actualiser** : bouton « Actualiser par une requête Oriane en direct ». Avant l'appel, confirmation : « Coût estimé : {cout_actualisation.credits_estimes} crédits ({cout_actualisation.methode}). Lancer ? » ; si `cout_actualisation` est `null` : « Coût non estimé par le service. Lancer ? ». La réponse (un radar) remplace l'écran ; une erreur 401 affiche `detail` tel quel.

**Une carte par élément de `recits[]`**, dans l'ordre rendu, sans tri ni classement :

- « Phrase surveillée » : `phrase_surveillee` entre « », en texte brut.
- « Requête envoyée à Oriane » : `requete_en_clair`.
- « Conversations observées » : pour chaque élément de `mesures[]`, « {valeur} {unite} » en grand, `nom` en petit, puis « Méthode : {methode} », « Fenêtre : du {fenetre.debut} au {fenetre.fin} », « Source : {source} », « Résultats consultés : {echantillon.resultats_consultes} (page de {echantillon.limite_page}) ». Si `echantillon.tronque` : « Échantillon tronqué : au-delà, rien n'a été lu ». Si `valeur` est `null` : « Non mesuré : {raison} ».
- Plus ancienne version : si `plus_ancienne_version` existe, son `libelle` tel quel suivi de « : {publie_le} », et un bouton qui ouvre la vidéo `plus_ancienne_version.video`.
- Liens sources : pour au plus trois identifiants de `videos[]`, dans l'ordre, `GET /v1/videos/{id}` puis `compte`, `plateforme`, `publie_le` et « Ouvrir sur la plateforme » (`lien`, nouvel onglet). Une 404 affiche `detail` à la place de la ligne.
- « Non cherché » : `non_cherche[]` par le composant `Segments`, toujours visible, jamais replié.
- Bouton « Ouvrir le récit » : `GET /v1/recits/{identifiant}`, panneau latéral avec les mêmes champs et la liste complète de `videos[]`. Si `variantes` est présent (récit né d'une recherche), « Variantes cherchées » en liste ; `sous_recherches[]`, s'il est présent, montre `libelle`, `type` (`mots` : « tous les mots, dans n'importe quel ordre » ; `exacte` : « phrase exacte ») et `videos` ; les vidéos du récit sont l'union, comptées une fois.

**Supprimer le récit** : dans le panneau du récit, bouton « Supprimer le récit ». Confirmation : « La phrase surveillée et les vidéos que seule elle a trouvées seront retirées. Confirmer ? ». Après confirmation, `DELETE /v1/recits/{identifiant}` avec `X-Cle-Demo` ; la réponse (`exemples/suppression-recit.json`) s'affiche : « Récit supprimé : {videos_retirees} vidéos retirées, {videos_conservees} conservées », puis `avertissement` tel quel s'il existe ; recharge ensuite `GET /v1/radar`. 401 ou 404 : `detail` tel quel.

**Juger la pertinence** : dans le panneau du récit, bouton « Juger la pertinence des vidéos ». Confirmation : « Les vidéos du récit sont envoyées au modèle de langue du service pour être jugées. Aucun crédit Oriane n'est dépensé. Lancer ? ». Après confirmation, `POST /v1/recits/{identifiant}/pertinence` avec `X-Cle-Demo` (corps vide, ou `{"forcer": true}` pour rejuger) ; la réponse (`exemples/pertinence-recit.json`) s'affiche : « {classees} vidéos jugées pour « {question} » par {modele} : {fortes} fortes, {faibles} faibles, {hors_sujet} hors sujet ; {non_classees} sans jugement », puis `avertissement` tel quel. Recharge ensuite les vidéos : chacune qui porte `pertinence` affiche « Pertinence jugée par {pertinence.modele} pour « {pertinence.question} » le {pertinence.calcule_le} : {forte, faible ou hors sujet} » puis `pertinence.motif` en texte brut. C'est une annotation : elle ne masque, ne trie et ne supprime aucune vidéo.

**Panneau vidéo** (geste j'ouvre une vidéo) : `compte`, `plateforme`, `identifiant_plateforme`, `publie_le` ; « {vues_selon_oriane} vues selon Oriane » et « {interactions_selon_oriane} interactions selon Oriane » (« non fourni » si `null`) ; « Légende » : `legende` ; « Trouvée par : » `requetes_trouvees[]` ; « Transcription lue chez {transcription.source} (niveau {transcription.niveau}) le {transcription.lue_le} » puis `transcription.texte` ; « Texte à l'écran lu chez {texte_ecran.source} le {texte_ecran.lue_le} » puis `texte_ecran.texte` ; « Ouvrir sur la plateforme » (`lien`). Tous les textes en texte brut.

**Comparer** : dans le panneau d'un récit, bouton « Comparer deux versions » : choisir « Source » (par défaut `plus_ancienne_version.video`) et « Reprise » parmi `videos[]`, deux vidéos distinctes ; `POST /v1/comparaisons` avec `{"video_source": …, "video_reprise": …}` et l'en-tête `X-Cle-Demo` ; puis naviguer vers `/versions/{identifiant}` de la réponse. Erreur : `detail` tel quel.

**États** : `recits` vide → « Aucun récit calculé. » ; récit dont `videos` est vide → « Aucune vidéo trouvée pour cette phrase dans les sources consultées. Voir ce qui n'a pas été cherché. » ; erreur → composant `ErreurService` ; données d'essai → bandeau du prompt 00.

**Donnée d'essai** : `exemples/radar.json` a deux récits : l'un avec deux vidéos (`vid-fictive-0001`, `vid-fictive-0002`), l'autre sans vidéo (état vide, `vues_cumulees` à `null` avec sa raison). `exemples/recit.json` est le récit qui a deux vidéos ; les deux exemples de vidéo répondent pour `GET /v1/videos/{id}`.

**Interdits** : aucun mot refusé d'`AGENTS.md` ; aucun classement, aucune jauge, aucune flèche de hausse ou de baisse, aucun pourcentage calculé ; aucune mesure sans sa méthode et sa fenêtre ; aucun appel Oriane direct.

Critère de fin : avec les données d'essai, la carte du récit à deux vidéos montre « 2 vidéos », « 2 comptes », « 42200 vues selon Oriane » chacune avec sa méthode et sa fenêtre, la plus ancienne version retrouvée au 04/11/2026, cinq lignes « Non cherché » ; l'autre carte affiche l'état vide.
