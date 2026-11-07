# Kit des trois écrans Lovable

Trois écrans (Radar des récits, Versions côte à côte, Fiche de vérification) et une barre d'état commune, branchés sur le seul service « Tête de Brut. » par son contrat `api.v1`.
Un cas, un parcours, cinq gestes : je découvre un récit, j'ouvre une vidéo, je compare une reprise, je vois ce qui a changé, j'enregistre une décision.
Ce dossier suffit à construire les écrans sans lire le code du service ; chaque champ cité ci-dessous existe mot pour mot dans `02_Service/contrats/api.v1.json`.

| Fichier | Rôle |
|---|---|
| `AGENTS.md` | Instructions de projet Lovable, à coller dans les réglages du projet et à poser à la racine du projet Lovable |
| `prompts/00-projet.md` à `prompts/03-fiche.md` | Un prompt de mode Plan par étape, dans l'ordre de construction |
| `exemples/*.json` | Une réponse par route, fictive, en mode `enregistre`, validée par les modèles du service (`02_Service/tests/test_exemples_ecrans.py`) |
| `README.md` | Ce brief : zones, champs par chemin JSON, gestes et appels, états, textes fixes |

Les exemples sont fictifs : une ville fictive, des comptes `compte_fictif_*`, des phrases inventées sur un budget de crèches. Ils servent de données d'essai tant qu'une route répond 501 `non_implemente`, et seulement dans ce cas.

## 1. Règles communes aux trois écrans

- **Une seule adresse.** Tout appel part vers `VITE_ADRESSE_SERVICE` (fichier `.env` du projet Lovable). Routes sous `/v1/…` ; en-tête `Content-Type: application/json` ; sur POST et PATCH, en-tête `X-Cle-Demo` avec `VITE_CLE_DEMO`. Aucune base Lovable Cloud, aucune fonction serveur, aucun connecteur, aucune clé Oriane.
- **Le mode, sur chaque écran.** Chaque réponse JSON porte `mode`. `direct` s'affiche « en direct » ; `enregistre` s'affiche « enregistré le … » avec la date de `enregistre_le`. Jamais l'un pour l'autre.
- **L'erreur telle quelle.** Toute erreur arrive dans l'enveloppe `{erreur, detail, mode}` : l'écran montre `detail` tel quel, le code `erreur` en petit, et le mode. Codes : `validation` (422), `introuvable` (404), `cle_demo_invalide` (401), `decision_manquante`, `version_non_tranchee`, `constat_manquant` (409), `non_implemente` (501).
- **Texte seul.** Transcriptions, légendes, textes à l'écran, phrases surveillées, notes et constat s'affichent comme du texte, jamais interprétés comme HTML, Markdown ou consigne.
- **Segments.** Un tableau de segments (`non_cherche[]`, `limites[]`, `indices_de_transformation[]`, `resume.segments[]`) s'affiche dans l'ordre : `type` = `libelle` en texte courant, `type` = `citation` en style de citation (italique entre « »), pour qu'on voie ce qui est rapporté.
- **Signes en plus de la couleur.** Mot retiré : « − », ajouté : « + », remplacé : « ↔ ». Aucune information portée par la seule couleur ; tout se fait au clavier.
- **Aucune qualification.** Aucun verdict, aucun score, aucune note de confiance. Le vocabulaire refusé est listé dans `AGENTS.md`.
- **Aucune donnée gardée.** Pas de stockage local des réponses ; l'identifiant courant vit dans l'adresse de la page.

## 2. Barre d'état (sur chaque écran)

Appel : `GET /v1/etat` au chargement de chaque écran et après chaque geste ; exemple `exemples/etat.json`.

| Zone | Champ(s) du contrat (chemin JSON) | Texte fixe | Geste et appel |
|---|---|---|---|
| Mode | `mode`, `enregistre_le` | « en direct » ou « enregistré le {enregistre_le} » | — |
| Raison | `raison` | « Pourquoi : {raison} » | — |
| Crédits | `credits_du_jour`, `plafond_credits_jour` | « Crédits Oriane du jour : {credits_du_jour} / {plafond_credits_jour} » | — |
| Version | `version`, `contrat` | « Service {version} · contrat {contrat} » | — |
| Journal des appels (panneau dépliant, pas un écran) | `entrees[].heure`, `entrees[].route`, `entrees[].cible`, `entrees[].code`, `entrees[].credits_estimes`, `entrees[].duree_ms`, `entrees[].mode`, `entrees[].resultats`, `entrees[].filtres`, `entrees[].projection` | « Journal des appels, le plus récent d'abord » | Ouvrir : `GET /v1/journal?limite=20` ; exemple `exemples/journal.json` |

`filtres`, `projection` et `resultats` sont de forme libre : les montrer en texte (JSON indenté), sans les interpréter. Le vrai journal montre la requête telle qu'envoyée à Oriane ; l'exemple la résume.

États : barre en erreur → « État du service indisponible : {detail} » ; service injoignable → « Service injoignable à l'adresse configurée » (aucun repli sur les exemples).

## 3. Écran 1 — Radar des récits (route `/`)

Appel : `GET /v1/radar` ; exemple `exemples/radar.json`. Geste servi : **je découvre un récit**, puis **j'ouvre une vidéo**.

| Zone | Champ(s) du contrat (chemin JSON) | Texte fixe | Geste et appel |
|---|---|---|---|
| En-tête | `calcule_le`, `mode`, `enregistre_le`, `raison` | « Radar des récits » ; « Calculé le {calcule_le} » | — |
| Actualiser | `cout_actualisation.credits_estimes`, `cout_actualisation.methode` | « Actualiser par une requête Oriane en direct » ; confirmation « Coût estimé : {credits_estimes} crédits ({methode}). Lancer ? » ; sans `cout_actualisation` : « Coût non estimé par le service. Lancer ? » | `POST /v1/radar/actualiser` avec `X-Cle-Demo`, après confirmation ; la réponse (un `Radar`) remplace l'écran |
| Carte de récit : phrase | `recits[].phrase_surveillee` | « Phrase surveillée » ; la phrase entre « », citée telle quelle | — |
| Carte : requête | `recits[].requete_en_clair` | « Requête envoyée à Oriane » | — |
| Carte : conversations observées | `recits[].mesures[].valeur`, `recits[].mesures[].unite`, `recits[].mesures[].nom` | « Conversations observées » ; « {valeur} {unite} » | — |
| Carte : méthode de chaque mesure | `recits[].mesures[].methode`, `recits[].mesures[].fenetre.debut`, `recits[].mesures[].fenetre.fin`, `recits[].mesures[].source` | « Méthode : {methode} » ; « Fenêtre : du {debut} au {fin} » ; « Source : {source} » | — |
| Carte : échantillon | `recits[].mesures[].echantillon.resultats_consultes`, `recits[].mesures[].echantillon.limite_page`, `recits[].mesures[].echantillon.tronque` | « Résultats consultés : {resultats_consultes} (page de {limite_page}) » ; si `tronque` : « Échantillon tronqué : au-delà, rien n'a été lu » | — |
| Carte : valeur absente | `recits[].mesures[].raison` (quand `valeur` est `null`) | « Non mesuré : {raison} » | — |
| Carte : plus ancienne version | `recits[].plus_ancienne_version.libelle`, `recits[].plus_ancienne_version.publie_le`, `recits[].plus_ancienne_version.video` | le texte de `libelle`, suivi de « : {publie_le} » | Ouvrir cette vidéo : `GET /v1/videos/{video}` |
| Carte : liens sources (trois au plus) | `recits[].videos[]`, puis pour chacun `compte`, `plateforme`, `publie_le`, `lien` de `GET /v1/videos/{id}` | « Ouvrir sur la plateforme » | `GET /v1/videos/{id}` par identifiant ; lien externe dans un nouvel onglet |
| Carte : non cherché (toujours ouvert) | `recits[].non_cherche[].texte` (segments) | « Non cherché » | — |
| Carte : ouvrir | `recits[].identifiant` | « Ouvrir le récit » | `GET /v1/recits/{identifiant}` ; exemple `exemples/recit.json` ; panneau du récit, mêmes champs plus la liste complète des vidéos |
| Panneau vidéo | `compte`, `plateforme`, `identifiant_plateforme`, `publie_le`, `vues_selon_oriane`, `interactions_selon_oriane`, `legende`, `requetes_trouvees[]`, `transcription.texte`, `transcription.source`, `transcription.niveau`, `transcription.lue_le`, `texte_ecran.texte`, `texte_ecran.source`, `texte_ecran.lue_le`, `lien` | « {vues_selon_oriane} vues selon Oriane » ; « {interactions_selon_oriane} interactions selon Oriane » ; « Légende » ; « Trouvée par : {requetes_trouvees} » ; « Transcription lue chez {transcription.source} (niveau {transcription.niveau}) le {transcription.lue_le} » ; « Texte à l'écran lu chez {texte_ecran.source} le {texte_ecran.lue_le} » | Geste **j'ouvre une vidéo** : `GET /v1/videos/{id}` ; exemples `exemples/video-source.json`, `exemples/video-reprise.json` |
| Comparer | `recits[].videos[]`, `recits[].plus_ancienne_version.video` | « Comparer deux versions » ; « Source » (par défaut la plus ancienne version retrouvée) ; « Reprise » | Geste **je compare une reprise** : `POST /v1/comparaisons` `{"video_source": id, "video_reprise": id}` avec `X-Cle-Demo`, puis aller à `/versions/{identifiant}` de la réponse |

États : `recits` vide → « Aucun récit calculé. » ; récit sans vidéo (`recits[].videos` vide) → « Aucune vidéo trouvée pour cette phrase dans les sources consultées. Voir ce qui n'a pas été cherché. », encart « Non cherché » ouvert ; erreur → enveloppe telle quelle ; 401 à l'actualisation → `detail` tel quel (exemple `exemples/erreur-401-cle-demo.json`).

## 4. Écran 2 — Versions côte à côte (route `/versions/:id`)

Appels : `GET /v1/comparaisons/{id}` (exemple `exemples/comparaison.json`), puis `GET /v1/videos/{video_source}` et `GET /v1/videos/{video_reprise}` pour les textes. Geste servi : **je vois ce qui a changé**.

| Zone | Champ(s) du contrat (chemin JSON) | Texte fixe | Geste et appel |
|---|---|---|---|
| En-tête | `identifiant`, `mode`, `enregistre_le`, `normalisation` | « Versions côte à côte » ; « Comparaison au mot, normalisation {normalisation} » | — |
| Colonne source / colonne reprise : fiche de la vidéo | `video_source`, `video_reprise`, puis `compte`, `plateforme`, `publie_le`, `vues_selon_oriane`, `lien` de chaque vidéo | « Source » ; « Reprise » ; « {vues_selon_oriane} vues selon Oriane » ; « Ouvrir sur la plateforme » | — |
| Attribution des transcriptions | `transcriptions.source.source`, `transcriptions.source.niveau`, `transcriptions.source.lue_le`, `transcriptions.reprise.source`, `transcriptions.reprise.niveau`, `transcriptions.reprise.lue_le` | « Transcription lue chez {source} (niveau {niveau}) le {lue_le}, non refaite sur la vidéo » | — |
| Parole, au mot | `operations[].type`, `operations[].position_source`, `operations[].position_reprise`, `operations[].mots_source[]`, `operations[].mots_reprise[]`, avec `transcription.texte` de chaque vidéo | « Parole » ; mots marqués « − » (retiré, colonne source), « + » (ajouté, colonne reprise), « ↔ » (remplacé, deux colonnes) | — |
| Légende, au mot | `ecart_legende[]` (mêmes champs), avec `legende` de chaque vidéo | « Légende » | — |
| Texte à l'écran, au mot | `ecart_texte_ecran[]` (mêmes champs), avec `texte_ecran.texte` de chaque vidéo | « Texte à l'écran » | — |
| Liste des écarts | `operations[]`, `ecart_legende[]`, `ecart_texte_ecran[]` | « Indices de transformation » ; par ligne « − retiré », « + ajouté » ou « ↔ remplacé », « à partir du mot {position + 1} », puis les mots entre « » ; décompte « {n} mots retirés · {n} ajoutés · {n} remplacés » | — |
| Heure dans la vidéo | `heure_dans_la_video.secondes`, `heure_dans_la_video.libelle` | « Heure dans la vidéo : {libelle} » quand `secondes` est `null` | — |
| Rappel | — | « L'écart décrit ce qui diffère, il ne dit pas pourquoi. » | — |
| Ouvrir la fiche | `identifiant` | « Ouvrir la fiche de vérification » | Geste **j'enregistre une décision** (début) : `POST /v1/fiches` `{"comparaison": identifiant}` avec `X-Cle-Demo` ; réponse 201 `Fiche` ; aller à `/fiche/{identifiant}` de la fiche |

Repérage des mots : les positions comptent les mots dès 0 après la normalisation `mots.v1` (règle donnée dans `prompts/02-versions.md`). L'écran découpe chaque texte selon cette règle, marque les mots aux positions données et vérifie qu'ils sont bien ceux de `mots_source` ou `mots_reprise` ; s'ils diffèrent, il ne marque rien et affiche « Repérage au mot indisponible pour ce texte : voir la liste des écarts. » Sous chaque colonne, le texte tel que lu chez Oriane reste lisible en entier.

États : les trois listes vides → « Aucun écart au mot relevé entre les deux versions. » ; vidéo introuvable (404) → `detail` tel quel dans sa colonne ; comparaison introuvable → `detail` tel quel et lien « Revenir au radar ».

## 5. Écran 3 — Fiche de vérification (route `/fiche/:id`)

Appel : `GET /v1/fiches/{id}` ; exemples `exemples/fiche-avant-decision.json` et `exemples/fiche-apres-decision.json`. Geste servi : **j'enregistre une décision**. Chaque geste rend la fiche entière : l'écran remplace son affichage par la réponse.

| Zone | Champ(s) du contrat (chemin JSON) | Texte fixe | Geste et appel |
|---|---|---|---|
| En-tête | `identifiant`, `comparaison`, `requete`, `mode`, `enregistre_le` | « Fiche de vérification » ; « Requête : {requete} » ; « Comparaison {comparaison} » | Lien « Revoir les versions » vers `/versions/{comparaison}` |
| Versions à trancher (deux cartes) | `versions[].video`, `versions[].lien`, `versions[].compte`, `versions[].date`, `versions[].vues_selon_oriane`, `versions[].etat`, `versions[].note` | « Versions à trancher : {nombre de versions dont etat = a_trancher} » ; états affichés « à trancher », « confirmée », « écartée » ; « Confirmer » ; « Écarter » ; « Note » | `PATCH /v1/fiches/{id}` `{"versions": [{"video": …, "etat": "confirmee" ou "ecartee", "note": …}]}` avec `X-Cle-Demo` |
| Indices de transformation | `indices_de_transformation[].type`, `indices_de_transformation[].texte` | « Indices de transformation » | — |
| Plus ancienne version | `plus_ancienne_version.libelle`, `plus_ancienne_version.publie_le`, `plus_ancienne_version.video` | le texte de `libelle`, suivi de « : {publie_le} » | — |
| Non cherché | `non_cherche[].texte` | « Non cherché » | — |
| Limites | `limites[].texte` | « Limites » | — |
| Résumé | `resume.segments[]`, `resume.methode` | « Résumé » ; « Rédigé par {methode}, à relire » | — |
| Constat | `constat` | « Votre constat » ; aide « Écrivez ce que vous avez établi. La machine n'écrit rien ici. » ; « Enregistrer le constat » | `PATCH /v1/fiches/{id}` `{"constat": …}` avec `X-Cle-Demo` ; champ vide à la création, jamais pré-rempli |
| Décision | `decision.valeur`, `decision.role`, `decision.note`, `decision.heure` | trois boutons « À vérifier » (`a_verifier`), « Ne pas amplifier » (`ne_pas_amplifier`), « Prêt à traiter » (`pret_a_traiter`) ; « Rôle » (par défaut « journaliste ») ; « Note » ; après : « Décision : {valeur affichée}, prise par {role} le {heure} » | `POST /v1/fiches/{id}/decision` `{"valeur": …, "role": …, "note": …}` avec `X-Cle-Demo` ; l'heure est posée par le service |
| Journal de la fiche | `journal[].heure`, `journal[].geste`, `journal[].detail` | « Journal de la fiche » | — |
| Export | — | « Exporter la fiche » ; « Rien n'est envoyé : l'export ouvre une page à relire. » | `GET /v1/fiches/{id}/export` : 200 `text/html` ouvert dans un nouvel onglet (adresse `blob:`), ou 409 dont `detail` s'affiche tel quel (exemple `exemples/erreur-409-decision-manquante.json`) |

Le bouton d'export reste actif : c'est le service qui refuse tant qu'une décision manque, qu'une version reste à trancher ou que le constat est vide, et l'écran montre le motif.

États : fiche introuvable → `detail` tel quel ; fiche neuve → constat vide, aucune décision, « Versions à trancher : 2 » ; erreur d'un geste → `detail` tel quel sous la zone du geste, la fiche affichée reste la dernière réponse reçue.

## 6. Ce que chaque écran montre d'Oriane

- **Radar** : la requête envoyée en clair (`recits[].requete_en_clair` : phrase exacte, fenêtre, niveau `default`), le nombre de résultats consultés (`echantillon.resultats_consultes`), la source de chaque mesure (`mesures[].source`) et les vues « selon Oriane », jamais recomptées. Ce que le service calcule au-dessus : le regroupement en récits et les mesures, chacune avec sa méthode et sa fenêtre.
- **Versions côte à côte** : les deux transcriptions sont celles d'Oriane, au niveau `default`, lues à l'heure dite (`transcriptions.source.lue_le`, `transcriptions.reprise.lue_le`). Ce que le service calcule au-dessus : l'écart au mot (`normalisation` = `mots.v1`).
- **Fiche** : ce que le service a fait (regroupement, écart au mot, résumé par `resume.methode`) et ce qu'il n'a pas fait (`limites[]` : aucune transcription refaite, vues non recomptées ; `non_cherche[]`).
- **Barre d'état** : le mode et sa raison, les crédits Oriane du jour, et le journal de chaque appel parti vers Oriane.

## 7. Ce que le contrat ne donne pas, et comment l'écran fait

- L'enveloppe d'erreur ne porte pas `enregistre_le` : la date du cas vient de la barre d'état (`GET /v1/etat`).
- Un récit ne donne que les identifiants de ses vidéos (`recits[].videos[]`) : compte, date et lien viennent d'un `GET /v1/videos/{id}` par vidéo (trois au plus sur la carte).
- Une comparaison ne porte ni les textes ni les listes de mots normalisés : l'écran lit les deux vidéos et refait la découpe `mots.v1`, avec la vérification décrite au § 4.
- `apercu` (vidéo) est facultatif : `vignette` (adresse ou nul), `images_cles` (dix adresses au plus), `source` (toujours Oriane), `lue_le`. Il est absent quand Oriane ne sert rien : l'écran n'affiche alors aucune image et ne devine aucune adresse. Les adresses viennent d'Oriane, jamais construites par l'écran ; elles peuvent expirer, l'écran garde un repli sans image.
- `mesures[].nom` est un code (`videos_trouvees`, `comptes_distincts`, `vues_cumulees`) : l'écran affiche `unite` à côté de la valeur et `nom` en petit.

## 8. Mode d'emploi

1. **Créer le projet Lovable** (pile par défaut de Lovable) et coller le contenu de `AGENTS.md` dans les instructions du projet ([connaissance du projet](https://docs.lovable.dev/features/knowledge)). Le poser aussi à la racine du projet Lovable : il est relu à chaque message.
2. **Renseigner `.env`** à la racine du projet Lovable : `VITE_ADRESSE_SERVICE=https://<adresse du service>` et `VITE_CLE_DEMO=<clé de démonstration>`. Pas dans les Secrets de Lovable, réservés au code serveur, que ce projet n'a pas ([secrets](https://docs.lovable.dev/features/secrets)). La clé de démonstration est visible dans le navigateur : elle est de faible valeur, changée après le passage.
3. **Coller les prompts dans l'ordre**, chacun en [mode Plan](https://docs.lovable.dev/features/plan-mode) : `prompts/00-projet.md`, `01-radar.md`, `02-versions.md`, `03-fiche.md`. Relire le plan proposé, vérifier qu'il ne cite que des champs de ce brief, puis l'approuver ; un écran à la fois. Joindre ou coller le fichier d'exemple nommé par le prompt : il devient la donnée d'essai de l'écran.
4. **Donner les origines à P4** : l'origine exacte de l'aperçu Lovable et celle de la page publiée (schéma, hôte, port, lues dans la barre d'adresse), pour `ORIGINES_AUTORISEES` du service ; sinon le navigateur bloque l'appel (CORS).
5. **Vérifier** sur l'écran : le mode affiché, une erreur 401 sans la clé, l'export refusé avant la décision.

Par un assistant relié au [serveur MCP Lovable](https://docs.lovable.dev/integrations/lovable-mcp-server) : même ordre. L'assistant pose `AGENTS.md`, envoie chaque prompt en mode Plan, attend le plan, le compare à ce brief, l'approuve, puis passe au suivant ; il ne crée ni base, ni fonction serveur, ni connecteur.

Le code des écrans vit dans le dépôt créé par Lovable : la synchronisation Git de Lovable crée toujours un nouveau dépôt et n'importe pas un dépôt existant ([Git sync](https://docs.lovable.dev/integrations/git-sync-overview)). Ce dépôt garde le kit, seule source du brief ; un changement d'écran passe d'abord ici, puis dans Lovable. Branchement du service : `01_Docs/05_Integration/branchement-lovable-et-oriane.md`.
