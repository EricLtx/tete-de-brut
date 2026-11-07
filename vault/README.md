# Vault — mandats, revues, journal

| Dossier | Contenu | Dans Git |
|---|---|---|
| `mandats/` | Un fichier par mandat (`F001-sujet.md`), d'après `0000-gabarit-mandat.md` ; statut dans le frontmatter | Oui |
| `revues/` | Rapports de doublage (`F001-<sha7>.md` : mandat et sept premiers caractères du commit relu), d'après `0000-gabarit-revue.md` ; un `verdict: GO` du relecteur imposé (`relecteur:` égal à `relecteur.modele` de `config/harnais.json`) autorise la fusion du `commit` cité ; le rapport est commité avant le push de la branche protégée | Oui |
| `runtime/` | Journal machine `events.jsonl` écrit par la pipeline et les gardes | Non |

Cycle d'un mandat : `redige` → `lance` → `realise` → `en-doublage` → `go` ou `no-go` (retour à `realise`) → `fusionne` → `archive`.
