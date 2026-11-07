# Prompt 03 — Fiche de vérification

À coller tel quel en mode Plan, après le prompt 02. Joindre ou coller `exemples/fiche-avant-decision.json`, `exemples/fiche-apres-decision.json` et `exemples/erreur-409-decision-manquante.json` (données d'essai tant que les routes répondent 501).

---

Mode Plan. Construis l'écran **Fiche de vérification** sur la route `/fiche/:id`. Suis `AGENTS.md`. Propose le plan, puis attends mon approbation. Ne touche pas aux autres écrans.

**Geste servi** : j'enregistre une décision, puis l'export lisible.

**Appels** : `GET /v1/fiches/{id}` ; `PATCH /v1/fiches/{id}` (versions tranchées, constat) ; `POST /v1/fiches/{id}/decision` ; `GET /v1/fiches/{id}/export`. Chaque POST et PATCH porte `X-Cle-Demo`. Chaque geste rend la fiche entière : remplace l'affichage par la réponse, sans mise à jour optimiste.

**En-tête** : titre « Fiche de vérification » ; badge de mode ; « Requête : {requete} » ; « Comparaison {comparaison} » avec un lien « Revoir les versions » vers `/versions/{comparaison}`.

**Versions à trancher** : compteur « Versions à trancher : {nombre d'éléments de versions[] dont etat vaut a_trancher} ». Deux cartes, une par élément de `versions[]` : `video`, `compte`, `date`, « {vues_selon_oriane} vues selon Oriane », « Ouvrir sur la plateforme » (`lien`), état affiché « à trancher », « confirmée » ou « écartée » d'après `etat`, `note`. Boutons « Confirmer » et « Écarter » avec un champ « Note » : `PATCH /v1/fiches/{id}` avec `{"versions": [{"video": …, "etat": "confirmee" ou "ecartee", "note": …}]}`.

**Indices de transformation** : `indices_de_transformation[]` par le composant `Segments`.

**Plus ancienne version** : `plus_ancienne_version.libelle` tel quel, suivi de « : {plus_ancienne_version.publie_le} ».

**Non cherché** : `non_cherche[]` par `Segments`, toujours visible. **Limites** : `limites[]` par `Segments`, toujours visible.

**Résumé** : `resume.segments[]` par `Segments`, puis « Rédigé par {resume.methode}, à relire ».

**Constat** : zone de texte « Votre constat », aide « Écrivez ce que vous avez établi. La machine n'écrit rien ici. », valeur initiale `constat` (vide à la création). Jamais pré-remplie, aucune suggestion. Bouton « Enregistrer le constat » : `PATCH /v1/fiches/{id}` avec `{"constat": …}`.

**Décision** : champ « Rôle » (par défaut « journaliste »), champ « Note », trois boutons : « À vérifier » (`a_verifier`), « Ne pas amplifier » (`ne_pas_amplifier`), « Prêt à traiter » (`pret_a_traiter`). `POST /v1/fiches/{id}/decision` avec `{"valeur": …, "role": …, "note": …}` ; l'heure est posée par le service. Quand `decision` existe : « Décision : {libellé de decision.valeur}, prise par {decision.role} le {decision.heure} » et `decision.note`.

**Journal de la fiche** : titre « Journal de la fiche », une ligne par élément de `journal[]` : `heure`, `geste`, `detail`.

**Export** : bouton « Exporter la fiche », toujours actif, avec l'aide « Rien n'est envoyé : l'export ouvre une page à relire. » `GET /v1/fiches/{id}/export` : en 200 (`text/html`), ouvrir la page dans un nouvel onglet par une adresse `blob:` ; en 409, afficher `detail` tel quel sous le bouton (codes `decision_manquante`, `version_non_tranchee`, `constat_manquant`). Ne désactive jamais le bouton : c'est le service qui refuse.

**États** : fiche en 404 → `detail` et un lien « Revenir au radar » ; erreur d'un geste → `detail` sous la zone du geste, la fiche affichée reste la dernière reçue.

**Données d'essai** : `exemples/fiche-avant-decision.json` (constat vide, aucune décision, deux versions à trancher) au chargement ; `exemples/fiche-apres-decision.json` (deux versions confirmées, constat écrit, décision « À vérifier ») comme réponse d'essai des gestes ; `exemples/erreur-409-decision-manquante.json` comme réponse d'essai de l'export avant décision.

**Interdits** : aucun mot refusé d'`AGENTS.md` ; aucun constat rédigé par la machine ; aucun résumé produit par Lovable AI ; aucun verdict ni score ; aucune injection de la page exportée dans l'écran.

Critère de fin : avec les données d'essai, la fiche neuve affiche « Versions à trancher : 2 » et un constat vide ; l'export rend « La fiche n'a pas encore de décision : export refusé. » ; la fiche après décision affiche « Décision : À vérifier, prise par journaliste le 07/11/2026 à 09 h 20 » et cinq lignes de journal.
