---
mandat: F011
titre: S11 — Kit des trois écrans Lovable : brief écran par écran sur le contrat api.v1, instructions de projet, exemples de réponses validés, prompts de construction
statut: go
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S11
branche: feat/ecrans-lovable-kit (part de main à 2269c83)
worktree: .claude/worktrees/feat-ecrans-lovable-kit
modele: opus
effort: high
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a: 2026-11-07T11:36Z
rendu_a: 2026-11-07T12:00Z
go_a: 2026-11-07T12:25Z
allers_retours: 0
---

# F011 — S11, kit des trois écrans Lovable

Le mandat renvoie à la fiche S11 du plan, au contrat `02_Service/contrats/api.v1.json` et aux cinq schémas, aux modèles `02_Service/app/modeles.py`, au guide `01_Docs/05_Integration/branchement-lovable-et-oriane.md` et aux règles de confiance du `README.md`. Il ne les recopie pas. Effort `high` : chaque champ cité doit exister dans le contrat, mot pour mot.

## Objectif

Un dossier `03_Ecrans/` suffit à construire les trois écrans dans Lovable (par P2 au chat, ou par un assistant via le serveur MCP Lovable) sans relire le code : un brief par écran (zones, champs du contrat affichés, gestes et routes, états vide, erreur, mode enregistré), des instructions de projet prêtes à coller, des exemples de réponses JSON valides pour chaque route, et des prompts de construction en mode Plan, un par écran.

## Fichiers réservés

- `03_Ecrans/README.md` : brief des trois écrans (Radar des récits, Versions côte à côte, Fiche de vérification) et de la barre d'état ; pour chaque zone, le chemin JSON du champ affiché (`recits[].mesures[].methode`, …) ; les cinq gestes et leurs appels ; les textes fixes en français ; aucun écran de plus.
- `03_Ecrans/AGENTS.md` : instructions de projet Lovable, 10 000 caractères au plus (limite de la plateforme), à coller dans « Project settings → Instructions » et à poser à la racine du projet Lovable : une seule adresse `VITE_ADRESSE_SERVICE` et `VITE_CLE_DEMO` lues dans `.env`, aucune base Lovable Cloud, aucune fonction serveur, aucun connecteur, Lovable AI jamais sur le contenu ; textes des vidéos en texte seul ; `mode` affiché sur chaque écran ; enveloppe d'erreur montrée telle quelle ; vocabulaire refusé (mots de `02_Service/app/libelles.py` et « tendance », « viral », « manipulé », « faux » hors citation) ; signes − + ↔ en plus de la couleur.
- `03_Ecrans/prompts/00-projet.md`, `01-radar.md`, `02-versions.md`, `03-fiche.md` : un prompt de mode Plan par écran, dans l'ordre de construction, chacun renvoyant à l'exemple JSON à utiliser comme donnée d'essai tant que la route répond 501.
- `03_Ecrans/exemples/*.json` : une réponse par route du contrat (`etat`, `radar`, `recit`, `video`, `comparaison`, `fiche` avant et après décision, `journal`, une erreur 409 et une 401), en mode `enregistre` avec `enregistre_le`, cas fictif (aucune personne réelle), chaque mesure avec `methode` et `fenetre`.
- `02_Service/tests/test_exemples_ecrans.py` : chaque exemple est validé par le modèle pydantic de sa route (`Etat`, `Radar`, `Recit`, `Video`, `Ecart`, `Fiche`, `Journal`, `Erreur`) ; aucun segment `libelle` ne contient un libellé refusé ; aucun nom de champ Oriane.

Rien dans `02_Service/app/`, `contrats/` ni dans les autres tests : un champ manquant se signale dans les Échanges.

## État du poste

Python 3.13, venv à créer dans le worktree (`pip install -e '.[dev]'` dans `02_Service`). Pas de réseau nécessaire. Doc Lovable lue le 07/11 : Git sync crée toujours un nouveau dépôt (pas d'import), `AGENTS.md` à la racine lu à chaque message, variables `VITE_` dans `.env`, mode Plan avant tout code.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m ruff check . && python -m ruff format --check . && python -m pytest -q -m "not reel"   # vert, test_exemples_ecrans inclus
wc -c ../03_Ecrans/AGENTS.md    # ≤ 10000
04_Pipeline/ci.sh --ref feat/ecrans-lovable-kit   # « Pipeline locale verte »
```

## Compte rendu attendu (cinq lignes)

sha ; `git diff --stat origin/main...HEAD` ; dernière ligne de `ci.sh --ref` ; écarts à la fiche ; champs du contrat jugés manquants pour un écran.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-07 | réalisateur (opus / high) | Rendu 156cc92 (deux commits : `docs(ecrans)`, `test(service)`), 19 fichiers, tous dans la réserve. ruff et format propres, 232 tests verts (64 ajoutés), `AGENTS.md` 7 736 caractères, check-docs OK, run GitHub 42370512571 vert. Écarts déclarés : deux exemples de vidéo (source, reprise) ; exemple 501 ajouté, données d'essai affichées seulement sur 501 avec bandeau « fictives » ; exemples produits avec le gabarit de `feat/service-fiche` (à régénérer si S08 change ses textes) ; règle des mots refusés dans les `.md` : admis seulement entre accents graves. Champs jugés manquants au contrat (contournés côté écran) : `Erreur` sans `enregistre_le` ; `Recit.videos[]` identifiants seuls ; `Ecart` sans listes de mots normalisés (découpe refaite en JS, risque d'écart) ; origine parole ou texte à l'écran absente de `Recit` ; `Mesure.nom` en code ; `journal.filtres` porte des noms Oriane dans le vrai journal. Questions : ordre des refus d'export de S08 ; pile Lovable par défaut écrite de mémoire dans `AGENTS.md` ; `POST /v1/fiches` répété non documenté. |
| 2026-11-07 | orchestrateur | Vérifié sur le worktree : commits, diff dans la réserve, tests rejoués (232 verts), run GitHub vert. Statut `realise`, doublage lancé. Les champs manquants sont reportés au plan (journal d'alignement) pour décision après le hackathon ; aucun changement de contrat le 07/11. |
