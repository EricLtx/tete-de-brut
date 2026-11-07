# Tête de Brut.

Service d'API de la démonstration « Tête de Brut. » (hackathon Hack the Feed, piste éditoriale Brut, 07/11/2026) : lire l'intérieur des vidéos sociales pour donner à une rédaction un signal éditorial vérifiable, avec Oriane comme source dans la pipeline.

Ce dépôt ne contient que le code du service et son harnais de construction. La documentation de cadrage reste dans un dépôt privé.

- `02_Service/` : le service (Python, FastAPI, SQLite), ses contrats JSON et OpenAPI, ses tests.
- `01_Docs/` : décisions (ADR), plan de construction, registres.
- `04_Pipeline/` : pipeline locale et gardes git ; le workflow GitHub Actions rejoue le même script.
- `vault/` : mandats et rapports de relecture.

Règles de confiance du service : aucun verdict automatique, aucune métrique sans méthode, aucune donnée de tiers (commentaires, lieux, visages), transcriptions attribuées à leur source, mode « en direct » ou « enregistré le … » affiché sur chaque réponse.
