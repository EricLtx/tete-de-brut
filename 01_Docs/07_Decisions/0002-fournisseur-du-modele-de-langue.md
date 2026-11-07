# ADR-0002 — Fournisseur du modèle de langue du résumé de fiche : Claude (API Anthropic) à la place de Scaleway

- **Statut** : Proposée — 07/11/2026
- **Portée** : fiche S10 du plan (résumé de la fiche rédigé par un modèle de langue) et tout appel à un modèle de langue par le service
- **Dépend de** / **Remplace** : [ADR-0001](0001-perimetre-et-pile-du-service.md), qui nommait Scaleway pour S10 ; ne remplace pas l'ADR-0001, en amende un point

## Contexte

- L'ADR-0001 prévoit un résumé de fiche optionnel (S10) chez Scaleway, identifiant du modèle en configuration, sortie toujours filtrée. Aucun code n'existe : `RESUME_MODE=gabarit` reste le défaut et le gabarit déterministe tient seul.
- L'équipe dispose d'une clé Claude et la juge plus utile à la démonstration ; elle a aussi demandé que le fournisseur reste remplaçable (Mistral ou autre).
- Les clés sont des secrets GitHub du dépôt (`ORIANE_API_KEY`, `ANTHROPIC_API_KEY`), jamais des fichiers.
- Le contenu des vidéos (propos de personnes publiques) est une donnée non fiable et personnelle ; l'envoyer à un tiers est une décision d'hébergement.

## Options

| Option | Avantages | Inconvénients |
|---|---|---|
| A. Scaleway (ADR-0001) | Hébergement européen, déjà décidé | Modèle déprécié chez Mistral, aucune clé disponible |
| B. Claude, appelé par `httpx` derrière une configuration générique | Clé disponible, aucune dépendance nouvelle, fournisseur remplaçable | Données envoyées à un tiers américain |
| C. Pas de modèle de langue | Aucun risque | Résumé limité au gabarit |

## Décision

Option B : S10 appelle l'API Messages d'Anthropic par `httpx`, sans SDK. La configuration est générique (`MODELE_LANGUE_URL`, `MODELE_LANGUE_API_KEY`, `MODELE_LANGUE_ID`) pour changer de fournisseur sans code. Ce qui part : les extraits `citation` de la comparaison (40 mots au plus) entre délimiteurs, jamais un compte, un lien ni un champ hors liste blanche. Ce qui revient : un résumé filtré (libellés refusés), marqué « rédigé par un modèle de langue, à relire », jamais un constat ni une décision. Le gabarit reste le repli, ligne au journal.

## Conséquences

- Les variables `SCALEWAY_*` de `.env.example` sont remplacées ; aucune dépendance ajoutée.
- Le résumé produit en direct est enregistré avec le cas : le mode enregistré ne dépend pas du réseau.
- Tests sans réseau (`httpx.MockTransport`) ; un test `reel` sauté sans clé.
- Conditions de révision : refus de l'équipe d'envoyer des extraits à un tiers, ou résumé qualifiant un contenu malgré le filtre.
