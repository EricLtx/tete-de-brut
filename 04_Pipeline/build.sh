#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Build et contrôles bloquants du code (canon harnais-pipeline) : exécute, dans l'ordre, les commandes
# pipeline.build puis pipeline.controles de config/harnais.json, depuis la racine passée en argument.
#   04_Pipeline/build.sh [racine]        (défaut : le dépôt qui contient ce script)
# Chaque projet renseigne ses commandes (npm ci && npm run build, pytest, cargo test…) ; le script, lui, ne change pas.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/lib/common.sh"
root="$(cd "${1:-$here/..}" && pwd)"; cd "$root"
run_list() { # run_list <clé> <libellé>
  local n=0
  while IFS= read -r cmd; do
    [ -n "$cmd" ] || continue; n=$((n + 1))
    step "$2 $n : $cmd"; bash -c "$cmd" || die "$2 en échec : $cmd"
  done <<EOF2
$(cfg "$1")
EOF2
  [ "$n" -gt 0 ] || info "$2 : aucune commande dans config/harnais.json (pipeline.$1)"
}
run_list pipeline.build "Build"
run_list pipeline.controles "Contrôle"
ok "Build et contrôles OK : $root"
