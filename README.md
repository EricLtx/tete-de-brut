# Tête de Brut

Service d'API de la démonstration « Tête de Brut. » (hackathon Hack the Feed, piste éditoriale Brut, 07/11/2026) : lire l'intérieur des vidéos sociales pour donner à une rédaction un signal éditorial vérifiable, avec Oriane comme source dans la pipeline.

Ce dépôt ne contient que le code du service et son harnais de construction. La documentation de cadrage reste dans un dépôt privé.

- `02_Service/` : le service (Python, FastAPI, SQLite), ses contrats JSON et OpenAPI, ses tests.
- `03_Ecrans/` : kit des trois écrans Lovable (brief sur le contrat, instructions de projet, exemples de réponses, prompts) ; le code des écrans vit dans le dépôt créé par Lovable.
- `01_Docs/` : décisions (ADR), plan de construction, registres.
- `04_Pipeline/` : pipeline locale et gardes git ; le workflow GitHub Actions rejoue le même script.
- `vault/` : mandats et rapports de relecture.

Règles de confiance du service : aucun verdict automatique, aucune métrique sans méthode, aucune donnée de tiers (commentaires, lieux, visages), transcriptions attribuées à leur source, mode « en direct » ou « enregistré le … » affiché sur chaque réponse.

Vérifier le parcours d'un service lancé : `cd 02_Service && python scripts/verifier_parcours.py --adresse http://localhost:8080 --origine http://localhost:5173` rejoue santé, radar, vidéo, comparaison, fiche, décision, export et en-tête CORS, une ligne OK ou KO par geste, et sort avec le code 0 seulement si les huit sont OK. `CLE_DEMO`, si elle est dans l'environnement du script, est envoyée dans `X-Cle-Demo`. Le script n'actualise pas le radar (aucun crédit Oriane) mais écrit, sur le couple de vidéos pris à l'envers de la démonstration, une comparaison, une fiche, un constat et une décision « à vérifier » dans la base du service vérifié. Les huit règles transverses du service sont testées par `02_Service/tests/test_regles_transverses.py`.

Licence : licence commerciale « Tête de Brut. », droits réservés aux co-auteurs du projet (voir `LICENSE`). Le dépôt est public pour la lecture et l'intégration continue ; toute réutilisation demande l'accord écrit des co-auteurs.
