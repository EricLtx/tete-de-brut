---
mandat: F017
titre: S14 — Kit de l'écran Recherche : prompt 04, exemples recherche.v1 validés, README et AGENTS.md à quatre écrans, test du kit étendu
statut: redige
plan: 01_Docs/08_Plans/plan-service-demonstration.md
fiche: S14
branche: feat/ecrans-recherche-kit (part de main après fusion de S13)
worktree: .claude/worktrees/feat-ecrans-recherche-kit
modele: sonnet
effort: medium
relecteur: sonnet / high (config)
cree: 2026-11-07
lance_a:
rendu_a:
go_a:
allers_retours: 0
---

# F017 — S14, kit de l'écran Recherche

L'écran Recherche est construit dans Lovable le 07/11 par l'orchestrateur (MCP) d'après la spécification de S13 ; ce mandat la consigne dans le kit pour qu'elle soit relue, testée et rejouable. Il renvoie à `03_Ecrans/README.md`, `AGENTS.md`, `prompts/`, `exemples/` et `02_Service/tests/test_exemples_ecrans.py` ; il ne les recopie pas.

## Objectif

`03_Ecrans/prompts/04-recherche.md` (prompt de l'écran, route `/`, le Radar passant sur `/radar`) ; `exemples/recherche-preparee.json`, `recherche-executee.json`, `recherche-refus.json` validés par les modèles de S13 ; `README.md` : section des écrans à quatre entrées (Recherche en premier : zones, champs par chemin JSON, gestes « je cherche » et « je colle un lien », états vide, refus RG-02, 409 en mode enregistré) ; `AGENTS.md` : « exactement quatre écrans », routes et règles de la recherche (filtres affichés avant tout lancement, coût affiché, confirmation, aucun appel sans geste, refus affiché tel quel) ; `test_exemples_ecrans.py` : ensemble exact des prompts `00` à `04`, exemples de recherche validés, textes sans mot refusé.

## Fichiers réservés

`03_Ecrans/README.md`, `03_Ecrans/AGENTS.md`, `03_Ecrans/prompts/04-recherche.md`, `03_Ecrans/prompts/01-radar.md` (route `/radar`), `03_Ecrans/exemples/recherche-*.json`, `02_Service/tests/test_exemples_ecrans.py`. Rien dans `02_Service/app/`.

## Commande de fin et sortie attendue

```bash
cd 02_Service && python -m pytest -q tests/test_exemples_ecrans.py   # vert
wc -c ../03_Ecrans/AGENTS.md   # 10000 au plus
```

## Compte rendu attendu (cinq lignes)

sha ; diff ; tests ; écarts ; points ouverts.

## Échanges

| Date | De | Message |
|---|---|---|
| 2026-11-09 | orchestrateur | Périmètre complété depuis la rédaction : le kit cite aussi `DELETE /v1/recits/{id}` (S16, bouton « Supprimer le récit »), `POST /v1/recits/{id}/pertinence` (S18) et le champ optionnel `Recit.variantes` (S17) dans `README.md` et `AGENTS.md`, d'après `contrats/api.v1.json` ; retirer l'exemption `SANS_EXEMPLE_JUSQU_A_S14` de `tests/test_exemples_ecrans.py`. Part de `main` après fusion de F020. Fichiers réservés inchangés. |
