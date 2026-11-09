# Registre des décisions

> Liste de toutes les décisions structurantes, avec leur statut et leurs liens. Le détail (contexte, options, conséquences) est dans chaque ADR, dossier [`07_Decisions/`](../07_Decisions/).
> Dernière mise à jour : 09/11/2026.

## 1. Décisions

| ADR | Sujet | Statut | Date | Lien avec d'autres décisions | Plan associé |
|---|---|---|---|---|---|
| [0001](../07_Decisions/0001-perimetre-et-pile-du-service.md) | Périmètre et pile du service de démonstration : trois écrans, un cas réel, service d'API dans ce dépôt public, écrans Lovable sur son contrat OpenAPI, transcriptions lues chez Oriane, SQLite, mode enregistré annoncé | Acceptée (07/11/2026) | 07/11/2026 | Transposée de l'ADR-0005 du dépôt privé de cadrage | [plan-service-demonstration](../08_Plans/plan-service-demonstration.md) |
| [0002](../07_Decisions/0002-fournisseur-du-modele-de-langue.md) | Fournisseur du modèle de langue du résumé de fiche (S10) : Claude à la place de Scaleway, configuration générique | Acceptée (07/11/2026) | 07/11/2026 | Amende un point de l'ADR-0001 | `plan-service-demonstration.md`, fiche S10 |
| [0003](../07_Decisions/0003-pipeline-de-recherche-a-phases.md) | Pipeline de recherche à phases (lot 2) : machine à états à huit phases suivie par l'écran Recherche, exécution asynchrone et transitions append-only, sous-recherches typées par l'ontologie, corpus local FTS5 et cache exact Oriane, routage des modèles Anthropic par tâche, contrat `execution.v1` additif ; amendement A1 proposé le 10/11/2026 (sept étapes, phase `verification`) | Proposée | 09/11/2026 | Dépend de l'ADR-0001 (pile close, inchangée) ; amende l'ADR-0002 sur ce qui part vers le modèle | [plan-service-demonstration](../08_Plans/plan-service-demonstration.md), section « Lot 2 », fiches S21 à S39 |
| [0004](../07_Decisions/0004-versions-rapprochees-et-intendance-des-transcriptions.md) | Versions rapprochées et écarts de provenance constatés (lot 3) : regroupement des vidéos par leur texte et comparaison un à un par le code, sans affirmation sur l'origine synthétique d'un média ; Claude borné à annoter, expliquer et proposer ; intendance des transcriptions par corrections proposées et validées par une personne, texte d'Oriane jamais remplacé ; ontologie v2 portant les règles de confiance ; contrat additif | Proposée | 09/11/2026 | Dépend de l'ADR-0001 (pile close, inchangée), de l'ADR-0002 et de l'ADR-0003 (client Claude, FTS5, ontologie, mesures) ; deux fiches sous condition amenderaient l'ADR-0002 ou la liste blanche | [plan-service-demonstration](../08_Plans/plan-service-demonstration.md), section « Lot 3 », fiches S40 à S59 |
| [0005](../07_Decisions/0005-hebergement-durable-du-service.md) | Hébergement durable du service : machine toujours active à Paris, un processus où tourne le moteur d'exécutions, volume persistant hors image, sauvegarde quotidienne, nom de domaine stable, sonde externe ; conditions d'entrée du lot 2 (magasin concurrent, crédits par réservation, bascule datée, accès renforcé) | Proposée | 09/11/2026 | Amende la règle 5 de l'ADR-0001 ; tient l'engagement de l'ADR-0003 sur l'hébergement ; issue de la revue d'architecture du 09/11 (dépôt privé) | [plan-service-demonstration](../08_Plans/plan-service-demonstration.md), fiches S21 et S25 |

Statuts : Proposée, Acceptée, Amendée, Remplacée par XXXX, Abandonnée.

## 2. Décisions à prendre

| Sujet | Pourquoi maintenant | Qui tranche | Échéance |
|---|---|---|---|
| Licence du dépôt public | Décidée le 07/11/2026 : licence commerciale « Tête de Brut. », droits réservés aux co-auteurs (`LICENSE`) | Propriétaire du dépôt | Fait |
| Acceptation de l'ADR-0003 (pipeline de recherche à phases) | Toutes les fiches du lot 2 sauf S22 et S24 l'attendent | Propriétaire du dépôt | Avant S21 |
| Nom du produit | « Brut » dans le nom expose le produit à un droit antérieur (rapport de veille du 09/11, ce n'est pas un avis juridique) ; touche le titre du contrat et la licence ; fiches S38 et S39 prêtes sans nom | Propriétaire du dépôt (ADR conseillée) | Avant tout usage public |
| Acceptation de l'ADR-0005 (hébergement durable du service) ; choix de l'hébergeur, du nom de domaine et du budget | Le Codespace se met en veille ; conditionne la reprise des exécutions et le flux SSE (S37) | Propriétaire du dépôt | Avant l'ouverture à des utilisateurs |
| Acceptation de l'ADR-0004 (versions rapprochées, intendance des transcriptions) | Toutes les fiches du lot 3 l'attendent ; nom de la fonction, libellés refusés étendus, intendant du glossaire, identifiant du son et images clés à trancher (tâches HL6, HL8, HL9, HL11) | Propriétaire du dépôt | Avant S40 |
