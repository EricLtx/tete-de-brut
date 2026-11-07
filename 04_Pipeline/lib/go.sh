# Rapports de doublage : un merge dans la branche protégée n'est accepté que si le commit fusionné
# est couvert par un rapport « verdict: GO » dans vault/revues/ (règle du harnais, voir skill harnais-doublage).
# Usage : go_report_for <sha complet>   → imprime le chemin du rapport et retourne 0, sinon 1.
# Le rapport doit nommer le relecteur imposé par la config (relecteur.modele) : un GO d'un autre modèle ne compte pas.
go_report_for() {
  local root sha="$1" f modele
  root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  local dir="$root/$(cfg mandats.revues vault/revues)"
  modele="$(cfg relecteur.modele opus)"
  [ -d "$dir" ] || return 1
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    grep -qE "^commit:[[:space:]]*$sha[[:space:]]*$" "$f" || continue
    grep -qE "^verdict:[[:space:]]*GO[[:space:]]*$" "$f" || continue
    grep -qE "^relecteur:[[:space:]]*$modele[[:space:]]*$" "$f" || continue
    printf '%s\n' "$f"; return 0
  done
  return 1
}

# Un chemin correspond-il à un motif de la config ? Motifs : préfixe de dossier (« 01_Docs/ »), motif glob sur le chemin
# complet (« CLAUDE.md », « 02_Design/*.md » ; « * » traverse les « / »), exclusion par « ! » (« !.claude/skills/ »).
# Usage : path_matches <chemin> <motif>
path_matches() {
  local p="$1" pat="$2"
  case "$pat" in
    */) case "$p" in "$pat"*) return 0 ;; esac ;;
    *)  case "$p" in $pat) return 0 ;; esac ;;
  esac
  return 1
}

# Le chemin est-il « documentation seule » (docsSeulement) ? Une exclusion « !motif » l'emporte sur toute inclusion.
is_docs_only_path() {
  local p="$1" pat included=1
  while IFS= read -r pat; do
    [ -n "$pat" ] || continue
    case "$pat" in
      !*) path_matches "$p" "${pat#!}" && return 1 ;;
    esac
  done <<EOF2
$(cfg docsSeulement)
EOF2
  while IFS= read -r pat; do
    [ -n "$pat" ] || continue
    case "$pat" in !*) continue ;; esac
    path_matches "$p" "$pat" && return 0
  done <<EOF3
$(cfg docsSeulement)
EOF3
  return 1
}

# Commits en cours de fusion : MERGE_HEAD s'il existe (fusion interrompue ou conflit résolu), sinon les références
# de GIT_REFLOG_ACTION (« merge <réf>… », posé par git merge ; MERGE_HEAD n'existe pas encore pendant une fusion automatique).
merge_heads() {
  local gd r; gd="$(git rev-parse --git-dir)"
  if [ -f "$gd/MERGE_HEAD" ]; then cat "$gd/MERGE_HEAD"; return 0; fi
  case "${GIT_REFLOG_ACTION:-}" in
    merge\ *) for r in ${GIT_REFLOG_ACTION#merge }; do git rev-parse --verify --quiet "$r^{commit}" || die "Fusion refusée : référence « $r » introuvable"; done ;;
  esac
}

# Exige un rapport GO pour chaque commit fusionné ; meurt au premier qui en manque (pre-merge-commit, commit-msg).
# Suppose common.sh (info, die, cfg) et events.sh (harnais_event) chargés.
go_require_all() {
  local protected="$1" h report; shift
  for h in "$@"; do
    if report="$(go_report_for "$h")"; then
      info "Doublage GO : $(basename "$report") couvre ${h:0:7}"
      harnais_event merge ok "fusion dans $protected couverte par $(basename "$report")"
    else
      harnais_event merge ko "fusion dans $protected refusée : aucun rapport GO pour ${h:0:7}"
      die "Fusion dans $protected refusée : aucun rapport « verdict: GO » (relecteur $(cfg relecteur.modele opus)) dans $(cfg mandats.revues vault/revues) ne porte sur le commit ${h:0:7}. Lancer le doublage (skill harnais-doublage) puis refusionner ; « git merge --abort » annule la fusion en cours."
    fi
  done
}
