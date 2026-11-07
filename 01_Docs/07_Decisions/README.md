# Décisions d'architecture (ADR)

Chaque décision structurante est tracée ici, avec son contexte et ses conséquences, pour que toute session et toute personne qui reprend le projet sachent **pourquoi** les choses sont ainsi.

## Règles

- Un fichier par décision : `XXXX-sujet-en-minuscules.md`, numéro suivant dans l'ordre.
- Ne jamais réécrire une ADR acceptée : on la remplace par une nouvelle.
- Toute ADR ajoutée ou dont le statut change est reportée dans le [registre des décisions](../00_Index/registre-decisions.md), dans le même commit.
- Une ADR naît « Proposée » ; seul le responsable du projet la passe « Acceptée », et la date est notée.

## Gabarit

```markdown
# ADR-XXXX — Titre court de la décision

- **Statut** : Proposée — JJ/MM/AAAA
- **Portée** : périmètre concerné
- **Dépend de** / **Remplace** : liens vers les ADR concernées

## Contexte

Situation, contraintes, chiffres datés et sourcés.

## Options

| Option | Avantages | Inconvénients |
|---|---|---|

## Décision

Ce qui est retenu, en une phrase puis en détail.

## Conséquences

Ce que cela change, ce que cela coûte, ce qu'il faut surveiller ; conditions de révision.
```
