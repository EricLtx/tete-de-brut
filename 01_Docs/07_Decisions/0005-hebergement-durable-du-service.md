# ADR-0005 — Hébergement durable du service : une machine toujours active à Paris, un processus, disque persistant et nom stable

- **Statut** : Proposée — 09/11/2026
- **Portée** : où et comment tourne le service `02_Service/` après le hackathon, pour le POC à 5 ou 6 utilisateurs et pour le lot 2 (moteur d'exécutions de l'ADR-0003) ; ni la pile, ni le contrat `api.v1`, ni les écrans ne changent, sauf l'adresse qu'ils appellent
- **Dépend de** / **Remplace** : amende la règle 5 de l'[ADR-0001](0001-perimetre-et-pile-du-service.md) (conteneur sans serveur ou tunnel pour la démonstration) ; tient l'engagement de l'[ADR-0003](0003-pipeline-de-recherche-a-phases.md) (« hébergement durable, ADR séparée ») ; ne remplace rien. Issue de la revue d'architecture du 09/11/2026, conservée dans le dépôt privé de cadrage, qui porte le détail des mesures, de la notation et des risques

Conventions des chiffres : (F) fait relevé ou mesuré ; (E) estimation, calcul montré ; (H) hypothèse à vérifier.

## Contexte

- **Situation.** Le service tourne dans un Codespace GitHub lancé à la main, port public, base SQLite sur le disque du Codespace (F, journal d'alignement du plan, 09/11). Le 09/11, l'application Lovable publiée appelait une adresse qui ne répondait plus : le Codespace s'était arrêté (F), et rien ne l'a signalé. Un Codespace s'arrête après une période d'inactivité et peut être supprimé après une longue période sans usage (éditeur, documentation GitHub, durées à revérifier) ; c'est aussi un poste de développement, pas un hôte de production.
- **Exigences classées** (seuils (H), à valider par le propriétaire) :
  1. disponibilité et reprise : 99 % des sondes de 5 min réussies entre 8 h et 20 h les jours ouvrés ; une exécution coupée par un redémarrage reprend en moins de 60 s sans repayer de crédit ;
  2. sécurité de l'accès et des secrets ;
  3. maîtrise des crédits Oriane et des jetons : dépense bornée avant l'appel ;
  4. temps de réponse du suivi des exécutions : 95e centile < 300 ms ;
  5. évolutivité vers le lot 2 : un mandat par phase, contrat additif, tests sans réseau.
- **Ce que demande le lot 2.** L'ADR-0003 fait tourner des exécutions de 120 s au plus dans l'instance et les reprend au démarrage à partir de transitions écrites sur disque. Un hébergement sans disque persistant, comme un conteneur sans serveur (H, à vérifier chez l'hébergeur), perdrait la base à chaque arrêt.
- **Charge.** 5 ou 6 utilisateurs (F, plan) ; 6 écrans × 1 requête de suivi par seconde = 6 requêtes par seconde au pire, pendant les exécutions seulement (E) ; 600 crédits par jour ÷ 15 par page = 40 pages Oriane par jour au plus (E, plafond H).
- **Couplage avec les écrans.** L'adresse du service est écrite dans le code publié des écrans : chaque changement d'adresse impose une republication Lovable (F, plan).
- **Conditions déjà relevées dans le code** (détail dans la revue privée) : le magasin SQLite n'est pas encore réglé pour des lectures concurrentes d'un écrivain, contrairement à ce que prévoit l'ADR-0003 (D8) ; le calcul des crédits du jour et le verrou qui le protège ne tiendront pas la charge du lot 2 ; la bascule en mode enregistré ne se lève qu'au redémarrage, ce qui la figerait sur un hôte qui ne s'arrête plus ; l'accès au service doit être renforcé avant l'ouverture à des utilisateurs.

## Options

| Option | Avantages | Inconvénients |
|---|---|---|
| A. Rester dans le Codespace | Rien à faire, aucune compétence nouvelle | Arrêt après inactivité, panne constatée le 09/11 ; production dans un poste de développement ; coûteux s'il reste allumé (H) |
| B. Machine durable à Paris, un processus, volume persistant, nom de domaine propre (retenue) | Toujours active ; image du `Dockerfile` réutilisée ; ADR-0003 applicable telle quelle ; coût d'une petite instance (H, à relever) | Un redéploiement coupe les exécutions quelques secondes (E), reprises ensuite ; une seule copie du service possible ; une machine à administrer |
| C. Même machine, API et travailleur en deux processus, la base servant de file | Exécutions isolées des redéploiements de l'API ; boucle de l'API libre | Deux points d'entrée ; verrou des crédits à reconstruire en base avant tout usage ; travailleur à surveiller |
| D. Services gérés répartis : conteneur sans état, PostgreSQL géré, file gérée | Montée en charge ; disponibilité confiée à l'hébergeur | Révision de la pile close (ADR-0001) ; réécriture du magasin et des tests ; plusieurs services et lieux de secrets |

Notation pondérée de la revue (sur 500, recalculée par code) : B 390, C 358, D 301, A 251. Le classement tient sous cinq déplacements de 10 points de poids ; il ne s'inverse en faveur de C que si la reprise dans le processus échoue à l'essai et que le registre des crédits en base est déjà construit.

## Décision

Proposé au propriétaire : héberger le service sur une machine toujours active, en région Paris, de petite taille (2 vCPU et 2 Go environ (H)), qui fait tourner l'image du `Dockerfile` avec relance automatique, derrière un relais HTTPS sur un nom de domaine propre au projet, parce que c'est l'option qui tient l'exigence de disponibilité classée première au coût et au délai les plus bas sans toucher la pile close. Sept règles :

1. **Un processus.** `uvicorn` sans copies ; le moteur d'exécutions de l'ADR-0003 est une tâche du processus, lancée par une seule fonction de démarrage, qui pourra passer dans un second processus (option C) sans réécrire les phases.
2. **Données hors image.** La base et le cas enregistré sont sur un volume persistant monté ; l'image ne contient ni l'un ni l'autre, peut être construite par la CI et ne va jamais sur un registre public tant qu'elle porte des données.
3. **Sauvegarde.** Copie quotidienne par l'API de sauvegarde de `sqlite3` (bibliothèque standard), déposée hors de la machine, sept jours gardés, restauration essayée une fois avant l'ouverture.
4. **Nom stable.** Les écrans pointent vers le nom de domaine et sont republiés une seule fois ; un changement d'hébergeur ne touche plus que le DNS.
5. **Secrets.** Clés d'Oriane, du modèle et d'accès au service dans l'environnement de la machine, jamais dans l'image ni dans le dépôt ; renouvelées à la mise en service.
6. **Supervision.** Sonde externe sur `/sante` toutes les 5 min avec alerte ; `/sante` vérifie une lecture et une écriture en base.
7. **Conditions d'entrée du lot 2.** Avant S21 : magasin SQLite réglé pour des lectures concurrentes (WAL et lectures sans verrou d'écriture), registre des crédits par réservation, bascule datée, accès au service renforcé (décisions secondaires ci-dessous).

**Décisions secondaires, à rédiger** (chacune en ADR ou en amendement de l'ADR-0003) : accès au service par clé personnelle ; registre des crédits par réservation et bascule datée (amende G2 et G6 de l'ADR-0003) ; magasin SQLite concurrent (amende D8) ; observabilité minimale (sonde, identifiant de requête, durée par route, rapport quotidien de dépense) ; choix de l'hébergeur et du nom de domaine ; durée de conservation des données personnelles sur la machine et dans les sauvegardes.

## Conséquences

- **Positives** : le service répond quand les écrans l'appellent ; la reprise du lot 2 s'appuie sur un disque qui survit ; la production quitte le poste de développement ; un seul changement d'adresse pour toute la durée du POC.
- **Négatives, compromis acceptés** : un redéploiement interrompt brièvement les exécutions, qui reprennent sans repayer grâce aux caches exacts de l'ADR-0003 ; aucune montée en charge horizontale tant que la base est un fichier local (6 requêtes par seconde au pire (E), une machine suffit (H)) ; un coût fixe même les nuits sans usage ; une machine à administrer (mises à jour, certificat).
- **Risques** : panne non vue — sonde externe et alerte — propriétaire ; perte de la base — sauvegarde hors machine et essai de restauration — propriétaire ; reprise dans le processus non tenue — essai d'arrêt brutal pendant une exécution simulée avant la vague 3 (fiche S25), passage à l'option C si l'essai échoue.
- **Actions induites** : choisir l'hébergeur et le nom de domaine, relever le prix ; republier les écrans une fois ; mandat « production par l'image » (volume, CI sans le cas) ; mandats du magasin, des crédits, de la bascule et de l'accès ; décisions secondaires ci-dessus.
- **Conditions de révision.** Vers deux processus (option C) : l'essai d'arrêt brutal montre une reprise qui perd ou repaie ; plus de 5 % des exécutions d'une semaine finissent `interrompue` par redéploiement ; l'ADR-0004 introduit un travail de fond récurrent de plus de 2 min. Vers une base partagée (option D) : plusieurs copies du service deviennent nécessaires, ou la base dépasse 2 Go ou 50 écritures par seconde soutenues (H). Vers un autre hébergeur : une exigence de résidence des données de la rédaction, ou un prix relevé hors du budget validé.
