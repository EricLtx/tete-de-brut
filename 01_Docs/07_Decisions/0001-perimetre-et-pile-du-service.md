# ADR-0001 — Démonstration du 07/11/2026 : trois écrans, un cas réel, un service d'API construit par le harnais, écrans Lovable

Transposée de l'ADR-0005 du dépôt privé de cadrage ; ce dépôt public ne porte que le code du service.

- **Statut** : Proposée — 07/11/2026
- **Portée** : ce qui se construit le 07/11/2026 et comment ; l'architecture de campagne, décidée dans le dépôt privé, reste la cible après le hackathon
- **Dépend de** / **Remplace** : ne dépend d'aucune autre ADR de ce dépôt et ne remplace rien ; suspend pour la journée du 07/11 trois points de l'architecture de campagne (base dans Lovable Cloud, service de preuve avec transcription, tâche de nuit). Plan : [plan-service-demonstration](../08_Plans/plan-service-demonstration.md)

## Contexte

- La note de cadrage stratégique de l'équipe du 06/11/2026 (document HTML modifiable, hors dépôt) juge le concept solide et le prototype trop vaste : six vues, quinze flux, treize tables, plusieurs modèles, une tâche de nuit. Elle fixe la démonstration à **trois écrans, un cas vidéo réel, un parcours complet** : « Radar des récits » (détecter), « Versions côte à côte » (comparer), « Fiche de vérification » (décider). Elle demande d'ouvrir par le signal et non par l'architecture, de montrer Oriane « dans la boucle », de garder un seul moment de preuve, et de ne jamais présenter un parcours préparé comme un appel en direct.
- Le même document rappelle les règles de confiance déjà dans le cahier des charges v1.1 du dépôt privé : aucun « faux » automatisé, aucune métrique inventée, l'IA n'est pas une preuve, données utilisées légalement. Vocabulaire : « plus ancienne version retrouvée dans les sources consultées », « indices de transformation », « conversations observées ».
- La relecture des sources du 06/11 (relevé « Oriane et Brut », dépôt privé) établit qu'Oriane rend `media[].transcript` et `media[].onScreenText` dès le niveau `default` (15 crédits par page de 100). La comparaison de deux versions n'exige donc aucune transcription locale le 07/11 : Whisper, Scaleway et les modèles locaux ne sont pas nécessaires à la démonstration.
- Le harnais construit et relit du code dans ce dépôt (`04_Pipeline/ci.sh`, doublage, fusion). Les écrans se construisent dans Lovable, hors dépôt. Il faut une frontière nette entre les deux : ce que le harnais construit doit se tester seul, puis se connecter aux écrans.

## Options

| Option | Avantages | Inconvénients |
|---|---|---|
| A. Tout dans Lovable : écrans, fonctions serveur, base Lovable Cloud (architecture de campagne réduite à trois écrans) | Une seule pile, une seule équipe de construction, aucun hébergement à monter | Rien n'est testé par le harnais ; l'écart au mot, la fiche et les libellés refusés vivent dans du code généré sans tests ; la clé Oriane dans Lovable ; la connexion « système puis écrans » demandée par l'équipe n'existe pas |
| B. Un service d'API dans le dépôt (Python, base SQLite locale, clé Oriane dans l'environnement du service), écrans Lovable qui l'appellent en HTTPS (proposée) | Contrats versionnés et testés, relus par le harnais ; les écrans ne portent aucun secret ; le service se rejoue seul (démonstration de secours) ; même code demain sur un poste ou chez un hébergeur | Un hébergement à monter avant 12 h (conteneur Scaleway avec port ou tunnel depuis un poste) ; CORS ; deux lieux de code |
| C. Architecture de campagne en entier : écrans et base Lovable, guichet, travailleur Python avec transcription, tâche de nuit | Cible de campagne atteinte d'un coup | Trop de pièces pour une journée ; chaque dépendance peut bloquer le parcours ; c'est le risque que la note de cadrage demande d'écarter |

## Décision

Proposé à l'équipe : retenir l'option B, avec sept règles.

1. **Périmètre.** Trois écrans, un cas réel d'au moins deux vidéos comparables, un parcours : je découvre un récit, j'ouvre une vidéo, je compare une reprise, je vois ce qui a changé, j'enregistre une décision (« à vérifier », « ne pas amplifier », « prêt à traiter »). Tout le reste est reporté après le hackathon, sans être abandonné : l'architecture de campagne, décidée dans le dépôt privé, reste la cible après le hackathon.
2. **Transcriptions.** Lues chez Oriane au niveau `default` et attribuées à Oriane à l'écran. Aucune transcription locale le 07/11. Le résumé de la fiche se rédige d'abord par gabarit déterministe ; un modèle de langue (Mistral chez Scaleway, identifiant lu en configuration) n'intervient que si le gabarit tient et que le temps reste, et jamais sans le filtre des libellés refusés.
3. **Frontière.** Le harnais construit le service dans `02_Service/` : adaptateur Oriane, récits, écart au mot, fiche, décisions, journal des appels, contrat d'API décrit en OpenAPI. Les écrans Lovable consomment ce contrat et rien d'autre. Le contrat est écrit avant le premier écran. Pile du service, close : Python 3.12 dans l'image de conteneur, 3.12 ou 3.13 sur le poste (F : poste en 3.13 le 07/11), FastAPI avec pydantic, uvicorn, httpx, SQLite de la bibliothèque standard, pytest et ruff ; toute autre dépendance passe par une révision de cette ADR, jamais par un mandat.
4. **Base.** Pour la démonstration, le service garde ses données dans une base SQLite locale (cas enregistré, récits, comparaisons, décisions, journal). La base Lovable Cloud, le guichet et le rôle restreint ne sont pas montés le 07/11 ; l'essai du guichet n'est plus une porte de la journée.
5. **Hébergement de la démonstration.** Conteneur Scaleway Serverless Containers à Paris, avec port HTTP et route de santé, lancé avant 12 h (H) ; secours : service sur un poste de l'équipe exposé par un tunnel HTTPS. Les écrans pointent vers une seule adresse, changée en configuration.
6. **Mode enregistré.** Un vrai résultat Oriane est enregistré en JSON le matin, sans champ de tiers, puis rejoué si Oriane ne répond pas. Chaque écran affiche « en direct » ou « enregistré le … » ; jamais l'un pour l'autre. Le cas enregistré porte des comptes et des propos de personnes publiques : il reste hors Git (règle du dépôt qui interdit les données personnelles) et voyage dans l'image du conteneur ; les tests n'utilisent que des vidéos simulées.
7. **Dépôt.** Le code vit dans un dépôt public séparé ; la documentation de cadrage reste privée ; ce dépôt doit se suffire : plan, contrats, ADR.

## Conséquences

- Le plan [plan-service-demonstration](../08_Plans/plan-service-demonstration.md) découpe la journée en mandats du harnais (service) et renvoie les tâches humaines (requête Oriane réelle, choix du cas, écrans Lovable, pitch) au plan privé, en ne gardant que les dépendances des mandats envers elles ; deux jonctions, 12 h et 15 h 30, puis gel.
- `config/harnais.json → pipeline.build` est renseigné par le premier mandat de code (tests et vérification de style du service) ; les gardes s'appliquent sans exception : branche par mandat, `ci.sh` vert, rapport GO, fusion `--no-ff`.
- Le contrat suit les compléments de la revue d'architecture du 07/11 consignés au plan : routes sous `/v1` (sauf `/sante`), enveloppe d'erreur unique, champs en français et en `snake_case`, clé de démonstration optionnelle, comparaison idempotente, pas de passerelle d'API devant le service.
- Le cahier des charges v1.1 et le dossier d'architecture (dépôt privé) ne sont pas réécrits le 07/11 ; le plan en reprend les règles de confiance dans ses fiches. L'ordre de renoncement de la journée : d'abord le modèle de langue, puis l'indicateur de vitesse du radar, jamais la comparaison ni la fiche sourcée ni le mode affiché.
- Conditions de révision : Oriane ne rend pas de transcription exploitable pour le cas choisi (retour à une transcription Whisper chez Scaleway, portée par le service) ; le conteneur ne tient pas avant 12 h (tunnel) ; l'équipe préfère l'option A au démarrage (le plan garde alors les contrats et les tests comme spécification des fonctions Lovable).
