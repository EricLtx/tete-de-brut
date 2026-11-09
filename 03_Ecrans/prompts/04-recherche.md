# Prompt 04 — Recherche

À coller tel quel en mode Plan, après le prompt 03. Joindre ou coller `exemples/recherche-preparee.json`, `exemples/recherche-executee.json`, `exemples/recherche-refus.json`, `exemples/erreur-401-cle-demo.json`, `exemples/video-source.json`, `exemples/suppression-recit.json` et `exemples/pertinence-recit.json` (formes à afficher ; ils ne servent de données d'essai que si la route répond 501).

---

Mode Plan. Construis l'écran **Recherche** sur la route `/`. Suis `AGENTS.md`. Propose le plan (composants, appels, champs), puis attends mon approbation. Le Radar est sur `/radar` (prompt 01) ; ne touche ni à Versions ni à Fiche. Quatre écrans au total, aucun de plus.

**Gestes servis** : je cherche (une question libre) ; je colle un lien (une vidéo TikTok, Instagram ou YouTube).

**Appels** : `POST /v1/recherches/preparer` puis `POST /v1/recherches`, même corps `{"question": …}` (1 à 1 000 caractères), avec `X-Cle-Demo`. Aucun appel au chargement ni à la frappe : seul un clic envoie.

**Zone de saisie** : titre « Recherche » ; une zone de texte « Ta question ou le lien d'une vidéo » ; bouton « Préparer la recherche », inactif tant que la zone est vide.

**Après « Préparer »**, rien n'est lancé : l'écran montre ce qui partira chez Oriane, d'après la réponse (`recherche.v1`) :

- « Ta question devient {n} filtres » (type `phrase` ; n est le nombre d'éléments de `filtres.phrases` ; « 1 filtre » au singulier quand n vaut 1), avec la liste : `filtres.phrases[]`, chaque entrée citée entre « », l'étiquette « mots, dans n'importe quel ordre » pour celles qui figurent aussi dans `filtres.noyaux[]`, « phrase exacte » pour les autres.
- « Où » : `filtres.dans` ; « Fenêtre : du {filtres.fenetre.debut} au {filtres.fenetre.fin} » ; « Plateformes » : `filtres.plateformes[]`, ou « les trois » si la liste est vide ; « Comptes ciblés » : `filtres.comptes[]` s'il y en a ; « Comptes exclus » : `filtres.comptes_exclus[]` s'il y en a. Pour un lien : `filtres.plateformes[0]` et `filtres.identifiant_plateforme`, sans fenêtre.
- « Requête envoyée à Oriane » : `requete_en_clair`, telle quelle. Si `reformulation` vaut `modele`, la mention « Question reformulée par un modèle de langue » ; si `deterministe`, « Question traduite par règles ».
- « Coût estimé : {cout_estime.credits_estimes} crédits » et `cout_estime.methode` tel quel.
- Si `refus` existe : `refus.detail` tel quel, en évidence, et le bouton « Lancer la recherche » reste inactif. Aucune reformulation proposée.

**Lancer** : bouton « Lancer la recherche ». Confirmation : « Coût estimé : {cout_estime.credits_estimes} crédits ({cout_estime.methode}). Lancer ? ». Après confirmation, `POST /v1/recherches` avec `X-Cle-Demo` ; la réponse (201, `ResultatRecherche`) remplace l'affichage, le mode est affiché, et la barre d'état se recharge (`GET /v1/etat`).

- Type `phrase` : `recit` est le récit ajouté au radar. Affiche sa carte comme sur le Radar (phrase surveillée entre « », requête envoyée à Oriane, chaque mesure avec méthode, fenêtre, source et échantillon, plus ancienne version, « Non cherché » toujours visible), la liste de `videos[]` et le lien « Voir dans le radar » vers `/radar`. Si `recit.variantes` est présent, la liste « Variantes cherchées ». Boutons « Juger la pertinence des vidéos » et « Supprimer le récit » : mêmes gestes, textes et exemples (`exemples/pertinence-recit.json`, `exemples/suppression-recit.json`) que dans le prompt 01, avec deux écarts propres à cet écran. Après la pertinence, relis les vidéos du récit par `GET /v1/videos/{id}` (pas le radar). Après la suppression, affiche « Récit supprimé : {videos_retirees} vidéos retirées, {videos_conservees} conservées » puis `avertissement` tel quel, ne recharge pas `GET /v1/radar` (le radar est sur `/radar`), efface le récit de l'écran et rends la zone de saisie vide.
- Type `lien` : `video` est la vidéo retrouvée ; affiche-la comme le panneau vidéo du Radar. Le radar ne change pas.

**États et erreurs** : `refus` (voir ci-dessus, pas de lancement) ; 422 `validation` (question vide, ou recherche refusée au lancement) : `detail` tel quel ; 401 : `detail` tel quel (exemple `exemples/erreur-401-cle-demo.json`) ; 404 `introuvable` (lien : vidéo non retrouvée) : `detail` tel quel ; en mode enregistré, 409 `recherche_indisponible` : `detail` tel quel, mode visible ; 503 `oriane_injoignable` : `detail` tel quel, sans nouvel essai automatique ; service injoignable : « Service injoignable à l'adresse configurée ». Données d'essai : bandeau du prompt 00, seulement si la route répond 501 ; les routes de recherche sont servies, les exemples ne remplacent jamais un 409, un 422 ou un 503.

**Donnée d'essai** (forme à afficher, aucun repli) : `exemples/recherche-preparee.json` est une question libre reformulée en deux filtres (un noyau de mots, une phrase exacte), sur TikTok, hors deux comptes écartés, à 15 crédits ; `exemples/recherche-refus.json` est un nom seul refusé, à 0 crédit ; `exemples/recherche-executee.json` rend le récit de la phrase, deux vidéos.

**Interdits** : aucun mot refusé d'`AGENTS.md` ; aucun appel sans clic ; aucun filtre affiché qui diffère de ceux de la réponse ; aucun filtre ajouté par l'interface ; aucun appel Oriane direct ; aucun résultat gardé hors de l'écran.

Critère de fin : avec les données d'essai, la préparation affiche « Ta question devient 2 filtres » (« 1 filtre » pour le refus), la fenêtre du 31/10/2026 au 07/11/2026, « Coût estimé : 15 crédits » ; le refus affiche son `detail` sans bouton actif ; le lancement affiche le récit « places de crèche en 2027 » avec ses deux vidéos et le mode « enregistré le 07/11/2026 à 09 h 00 ».
