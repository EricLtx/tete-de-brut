# Banc d'évaluation du jeu d'or

Rejoue un jeu de questions contre un bras de recherche du service et écrit un rapport en comptes (fiche S22 du plan, mandat F024). Bibliothèque standard et `httpx` seulement ; aucun appel réseau dans les tests.

## Ce que le banc mesure

Pour chaque question du jeu : rappel@k (part des vidéos pertinentes trouvées à la main qui figurent parmi les `k` premières vidéos rendues), nDCG@k (même liste, avec le rang : une pertinente en tête vaut plus qu'en fin de liste), faits couverts (un fait attendu est couvert s'il figure tel quel, casse, accents et ponctuation ignorés, dans la légende, la transcription ou le texte à l'écran d'une des `k` premières vidéos), crédits dépensés, jetons, latence. La pertinence est binaire. `k` vaut 10 par défaut.

Le rapport donne des comptes (« 4 questions sur 6 ») et se lit comme un contrôle de cohérence : trente questions ne donnent pas une inférence statistique. Les jetons ne sont pas mesurés sur le bras `unique`, qui n'appelle aucun modèle ; la part de la synthèse rattachée à un extrait vient avec S32.

## Format `jeu.v1`

Schéma : `jeu.v1.schema.json`, vérifié par `evaluation/metriques.py` (`valider_jeu`). Un jeu a un nom, un budget de crédits de référence (entier, pour tout le jeu) et des questions. Chaque question a un identifiant unique, le texte envoyé tel quel à `POST /v1/recherches`, un à trois faits attendus et au moins une vidéo pertinente (identifiants du service). Un champ inconnu, un fait en trop ou un doublon refuse le jeu.

## Rejouer un jeu

```bash
cd 02_Service
python scripts/evaluer.py --jeu evaluation/donnees/jeu-or.json --bras unique --adresse http://localhost:8080
```

Options : `--k` (profondeur), `--sortie` (dossier des rapports, `evaluation/donnees/` par défaut). Si `CLE_DEMO` est dans l'environnement, elle est envoyée au service. Le rapport lisible et sa version JSON sont écrits dans le dossier de sortie et le premier est imprimé. Codes de sortie : 0 rapport écrit, 1 service injoignable, 2 jeu mal formé ou bras indisponible.

Bras : `unique` (la recherche actuelle) se rejoue ; `multi` et `boucle` sont déclarés et refusés avec « disponible à partir de S29 ».

## Données hors Git

Le jeu d'or réel (questions de la rédaction, vidéos retenues) et les rapports vivent dans `evaluation/donnees/`, ignoré par `evaluation/.gitignore`. Les rapports nomment les questions par leur identifiant, jamais par leur texte ni par un compte. Aucune question réelle ni réponse enregistrée n'entre dans le dépôt ; les tests n'utilisent qu'un jeu simulé.
