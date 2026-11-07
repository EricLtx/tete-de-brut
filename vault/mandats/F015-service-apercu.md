---
mandat: F015
titre: S12 — Aperçu des vidéos : vignette et images clés d'Oriane relayées dans video.v1 (champ apercu), liste blanche amendée, cas enregistré et données d'essai
statut: en-doublage
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S12
branche: feat/service-apercu (part de main)
worktree: .claude/worktrees/feat-service-apercu
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T13:36Z
rendu_a: 2026-11-07T13:44Z
go_a:
allers_retours: 0
---

# F015 — S12, aperçu des vidéos

Décision de l'équipe du 07/11/2026 (ADR-0007 du dépôt privé, Acceptée) : la liste blanche s'ouvre aux vignettes et aux images clés d'Oriane ; les écrans affichent aussi le lecteur officiel des plateformes (côté écrans, hors de ce mandat). Le mandat renvoie au contrat `02_Service/contrats/` et aux modèles `app/modeles.py` ; il ne les recopie pas.

## Objectif

`video.v1` porte un champ optionnel `apercu` : `{"vignette": <adresse ou null>, "images_cles": [<adresses>], "source": "Oriane", "lue_le": <date>}`, rempli depuis `thumbnailMediaUrl` et `media[].frames` d'Oriane quand ils sont présents, absent sinon ; le cas enregistré et les données d'essai du kit le portent ; aucun autre champ de tiers n'entre (commentaires, lieux, profils restent refusés). Contrat `api.v1` réexporté sans champ obligatoire nouveau : les écrans existants continuent de valider.

## Fichiers réservés

`02_Service/app/liste_blanche.py` (retrait de `thumbnailMediaUrl`, `thumbnailMediaId` et `frames` des refus ; table de correspondance vers `apercu`, un commentaire par champ), `app/modeles.py` (classe `Apercu` et champ `apercu: Apercu | None = None` sur `Video`), `contrats/video.v1.schema.json` et `contrats/api.v1.json` (réexport), `tests/test_oriane.py` (réponse simulée avec vignette et images clés : le champ est rempli ; sans : absent), `tests/conftest.py` (fixture enrichie), `03_Ecrans/exemples/video-source.json` et `video-reprise.json` (champ `apercu` avec des adresses fictives `https://exemple.invalid/…`), `03_Ecrans/README.md` § 7 (champ ajouté). Rien dans `app/routes/`, `app/ecart.py`, `app/fiche.py` : l'export HTML reste sans image.

## Règles de confiance (testées)

`apercu.source` vaut toujours « Oriane » ; aucune adresse déduite ou construite hors de la réponse d'Oriane ; `images_cles` limité à dix adresses ; aucun nom de champ Oriane dans le contrat ; aucun libellé refusé ; `test_exemples_ecrans` vert.

## État du poste

Python 3.12 hors PATH sur ce poste (`C:\Users\User\AppData\Local\Programs\Python\Python312`), venv avec ruff et pytest dans `C:\Users\User\AppData\Local\Temp\claude\venv-f011` ; sur l'autre poste, Python absent : vérification par le workflow GitHub.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert, test_exemples_ecrans inclus
gh run list --branch feat/service-apercu --limit 1   # completed success
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat origin/main...HEAD` ; run GitHub ; écarts ; adresses réelles à relever par P1 sur un résultat H01 (hôte, expiration).

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | orchestrateur (session service) | Lancé sur `feat/service-apercu` (worktree `.claude/worktrees/feat-service-apercu`), réalisateur sonnet / medium, en parallèle de F013 et F014 (aucun fichier commun). |
| 2026-11-07 | réalisateur sonnet / medium | Rendu aa7f98a762721f52269577a76d1a65fc2115ef22 : `Apercu` facultatif sur `Video`, liste blanche amendée (`thumbnailMediaId` reste refusé), images clés depuis `frames[].url` en `https://` sans doublon, dix au plus ; contrats réexportés sans champ obligatoire ; exemples du kit et README § 7 ; run 42378207683 vert, 305 tests. Hors réserve déclaré : `app/cas.py` (exemption de `vignette` dans les champs refusés), `tests/test_regles_transverses.py` (listes de champs de tiers). Fait relevé par l'orchestrateur dans la spécification OpenAPI Oriane (dépôt privé) : `frames` est une liste d'objets `{id, position, timestampSeconds, url, …}` servie au niveau `full` seulement ; au niveau `default` de la démonstration, seule la vignette arrive. Doublage sonnet / high lancé. |
