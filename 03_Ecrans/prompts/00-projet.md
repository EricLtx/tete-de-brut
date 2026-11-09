# Prompt 00 — Projet, module client, barre d'état et routage

À coller tel quel en mode Plan, une fois `AGENTS.md` posé. Joindre ou coller `exemples/etat.json`, `exemples/journal.json`, `exemples/erreur-401-cle-demo.json` et `exemples/erreur-501-non-implemente.json`.

---

Mode Plan. Prépare le socle du projet « Tête de Brut. », sans aucun écran métier encore. Suis les instructions du projet (`AGENTS.md`) ; propose le plan, liste les fichiers, attends mon approbation.

1. **Pile** : la pile par défaut du projet (React, TypeScript, Vite, Tailwind, shadcn/ui). Aucune base Lovable Cloud, aucune fonction serveur, aucun connecteur, aucune authentification, aucune fonction Lovable AI.
2. **Configuration** : lis `import.meta.env.VITE_ADRESSE_SERVICE` et `import.meta.env.VITE_CLE_DEMO` dans `src/lib/config.ts`. Crée `.env.example` avec ces deux noms, sans valeur. Si `VITE_ADRESSE_SERVICE` est vide, affiche « Adresse du service non configurée (VITE_ADRESSE_SERVICE) » sur chaque écran et n'appelle rien.
3. **Module client** `src/lib/service.ts` : une fonction par route du contrat `api.v1` (liste dans `AGENTS.md`), types TypeScript avec les noms exacts des champs (`mode`, `enregistre_le`, `raison`, `credits_du_jour`, `plafond_credits_jour`, `version`, `contrat` pour l'état ; `entrees[]` avec `id`, `heure`, `route`, `cible`, `filtres`, `projection`, `resultats`, `credits_estimes`, `duree_ms`, `code`, `mode` pour le journal ; `erreur`, `detail`, `mode` pour l'enveloppe d'erreur). En-tête `Content-Type: application/json` partout, `X-Cle-Demo` sur POST, PATCH et DELETE seulement. Une réponse non 2xx est lue comme enveloppe d'erreur et remontée telle quelle.
4. **Données d'essai** : range les fichiers joints dans `src/donnees-essai/`. Le module client ne les sert que si la route répond 501 avec `"erreur": "non_implemente"` ; il signale alors `essai: true` à l'écran, qui affiche le bandeau « Données d'essai fictives du kit : la route n'est pas encore servie ». Jamais sur une autre erreur ni quand le service est injoignable. Les routes de recherche, de suppression et de pertinence sont servies (200 ou 201) : leurs exemples fixent la forme à afficher et ne remplacent jamais une réponse du service, même en 409, 422 ou 503.
5. **Barre d'état** (composant `BarreEtat`, en haut de chaque écran), d'après `GET /v1/etat` au chargement et après chaque geste :
   - « en direct » si `mode` vaut `direct`, sinon « enregistré le {enregistre_le} » (date française, Europe/Paris) ;
   - « Pourquoi : {raison} » ;
   - « Crédits Oriane du jour : {credits_du_jour} / {plafond_credits_jour} » ;
   - « Service {version} · contrat {contrat} » ;
   - bouton « Journal des appels » qui déplie un panneau : `GET /v1/journal?limite=20`, titre « Journal des appels, le plus récent d'abord », une ligne par entrée avec `heure`, `route`, `cible`, `code`, `credits_estimes`, `duree_ms`, `mode` ; `filtres`, `projection` et `resultats` en JSON indenté, en texte brut, repliés par défaut.
   - En erreur : « État du service indisponible : {detail} ». Injoignable : « Service injoignable à l'adresse configurée ».
6. **Composants partagés** : `Mode` (badge « en direct » ou « enregistré le … », repris dans l'en-tête de chaque écran), `ErreurService` (affiche `detail` tel quel, le code `erreur` en petit et le mode), `Segments` (tableau de `{type, texte}` : `libelle` en texte courant, `citation` en italique entre « », dans l'ordre, en texte brut).
7. **Routage** : exactement quatre routes, `/` (Recherche), `/radar` (Radar des récits), `/versions/:id` (Versions côte à côte), `/fiche/:id` (Fiche de vérification), chacune pour l'instant un titre et la barre d'état. Aucune autre page.
8. **Accessibilité** : navigation au clavier, libellé texte sur chaque bouton, aucune information par la seule couleur.

Interdits : tout texte d'interface contenant un mot de la liste refusée d'`AGENTS.md` ; tout stockage local des réponses ; toute valeur de clé dans le code ; tout appel à une autre adresse que `VITE_ADRESSE_SERVICE`.

Critère de fin : avec les données d'essai, la barre d'état affiche « enregistré le 07/11/2026 à 09 h 00 », « Crédits Oriane du jour : 15 / 600 », « Service 0.1.0 · contrat api.v1 », et le panneau du journal liste deux lignes ; l'erreur 401 d'essai s'affiche par `ErreurService` avec « L'en-tête X-Cle-Demo est absent ou incorrect. »
