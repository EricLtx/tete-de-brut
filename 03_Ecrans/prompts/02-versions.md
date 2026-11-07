# Prompt 02 — Versions côte à côte

À coller tel quel en mode Plan, après le prompt 01. Joindre ou coller `exemples/comparaison.json`, `exemples/video-source.json` et `exemples/video-reprise.json` (données d'essai tant que les routes répondent 501).

---

Mode Plan. Construis l'écran **Versions côte à côte** sur la route `/versions/:id`. Suis `AGENTS.md`. Propose le plan, puis attends mon approbation. Ne touche pas au Radar.

**Geste servi** : je vois précisément ce qui a changé ; départ du geste j'enregistre une décision.

**Appels** : `GET /v1/comparaisons/{id}` ; puis `GET /v1/videos/{video_source}` et `GET /v1/videos/{video_reprise}` pour les textes ; `POST /v1/fiches` pour ouvrir la fiche.

**En-tête** : titre « Versions côte à côte » ; badge de mode ; « Comparaison au mot, normalisation {normalisation} ».

**Deux colonnes**, « Source » à gauche, « Reprise » à droite. Pour chacune : `compte`, `plateforme`, `publie_le`, « {vues_selon_oriane} vues selon Oriane », « Ouvrir sur la plateforme » (`lien`). Sous l'en-tête de colonne : « Transcription lue chez {transcriptions.source.source} (niveau {transcriptions.source.niveau}) le {transcriptions.source.lue_le}, non refaite sur la vidéo » (et `transcriptions.reprise.*` pour la reprise).

**Trois blocs alignés** dans chaque colonne, dans cet ordre :

1. « Parole » : `transcription.texte`, marqué avec `operations[]`.
2. « Légende » : `legende`, marqué avec `ecart_legende[]`.
3. « Texte à l'écran » : `texte_ecran.texte`, marqué avec `ecart_texte_ecran[]`.

**Marquage au mot.** Chaque opération a `type` (`retire`, `ajoute`, `remplace`), `position_source`, `position_reprise`, `mots_source[]`, `mots_reprise[]`. Les positions comptent les mots dès 0 après la normalisation `mots.v1`. Écris une fonction `motsV1(texte)` qui applique, dans l'ordre :

- forme Unicode composée (`normalize("NFC")`), puis minuscules ;
- apostrophes et traits d'union (`'`, `’`, `ʼ`, `‘`, `` ` ``, `´`, `-`, `‐`, `‑`, `‒`, `–`, `—`, `―`, `−`) changés en espace, ainsi que tout blanc ;
- virgule ou point gardé seulement entre deux chiffres (« 3,5 » reste un mot) ;
- autre caractère gardé seulement s'il est une lettre, une marque diacritique ou un chiffre (`\p{L}`, `\p{M}`, `\p{N}`), sinon retiré ;
- découpage sur les espaces, mots vides ignorés.

Affiche les mots rendus par `motsV1` : dans la colonne source, les mots `position_source` à `position_source + mots_source.length - 1` ; dans la colonne reprise, les mots `position_reprise` à `position_reprise + mots_reprise.length - 1`. Signe et style : `retire` « − » (barré, colonne source), `ajoute` « + » (souligné, colonne reprise), `remplace` « ↔ » (dans les deux colonnes). Le signe est écrit devant le mot, la couleur ne fait que doubler. Avant de marquer, vérifie que les mots trouvés sont égaux à `mots_source` (ou `mots_reprise`) ; sinon ne marque rien dans ce bloc et affiche « Repérage au mot indisponible pour ce texte : voir la liste des écarts. » Sous chaque bloc, un dépliant « Texte tel que lu chez Oriane » montre le texte brut entier.

**Liste des écarts**, sous les colonnes, titre « Indices de transformation » : une ligne par opération, groupées par « Parole », « Légende », « Texte à l'écran » ; « − retiré », « + ajouté » ou « ↔ remplacé », « à partir du mot {position + 1} », puis les mots entre « ». Décompte par bloc : « {n} mots retirés · {n} ajoutés · {n} remplacés » (somme des longueurs de `mots_source` pour retiré et remplacé, de `mots_reprise` pour ajouté).

**Heure dans la vidéo** : « Heure dans la vidéo : {heure_dans_la_video.libelle} » quand `heure_dans_la_video.secondes` est `null`.

**Rappel fixe** en bas : « L'écart décrit ce qui diffère, il ne dit pas pourquoi. »

**Ouvrir la fiche** : bouton « Ouvrir la fiche de vérification » : `POST /v1/fiches` avec `{"comparaison": identifiant}` et `X-Cle-Demo` ; réponse 201 ; naviguer vers `/fiche/{identifiant}` de la fiche rendue. Erreur : `detail` tel quel.

**États** : les trois listes vides → « Aucun écart au mot relevé entre les deux versions. » ; vidéo en 404 → `detail` dans sa colonne ; comparaison en 404 → `detail` et un lien « Revenir au radar ».

**Donnée d'essai** : dans `exemples/comparaison.json`, la parole a un mot remplacé (« trois » ↔ « cinq ») et huit mots retirés (« si le budget annexe est voté en décembre ») ; la légende et le texte à l'écran ont chacun un remplacement (« 300 » ↔ « 500 ») et un retrait.

**Interdits** : aucun mot refusé d'`AGENTS.md` ; aucun pourcentage de ressemblance, aucun score, aucune qualification de l'écart ; aucune couleur seule ; aucun texte de vidéo rendu en HTML.

Critère de fin : avec les données d'essai, « trois » et « cinq » portent « ↔ », les huit mots retirés portent « − » dans la colonne source, et le décompte de la parole affiche « 8 mots retirés · 0 ajoutés · 1 remplacés ».
