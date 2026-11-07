#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Pipeline de contrôle locale (canon harnais-pipeline) : rejoue build.sh et check-docs.sh sur le dernier commit
# d'une branche, extrait dans un worktree temporaire (jamais la copie de travail), selon les fichiers touchés.
#   04_Pipeline/ci.sh [--ref <branche>] [--origin] [--all]
# Portée : fichiers changés par rapport à origin/<branche protégée>, branche protégée comprise (un push de
# documentation seule sur main ne relance pas le build). Documentation = docsSeulement, *.md et configs de lint ;
# tout le reste déclenche build.sh. Rien de changé (ci.sh lancé à la main sur main à jour) ou --all : tout tourne.
# Aucun contrôle ne peut être sauté : en cas d'échec, corriger la cause.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/lib/common.sh"; . "$here/lib/events.sh"; . "$here/lib/go.sh"
ref_opt=""; mode=local; all=0
while [ $# -gt 0 ]; do
  case "$1" in
    --ref) ref_opt="${2:?--ref attend une branche}"; shift ;;
    --origin) mode=origin ;;
    --all) all=1 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) die "Argument inconnu : $1" ;;
  esac; shift
done
need git
repo="$(git -C "$here" rev-parse --show-toplevel)"
export HARNAIS_ROOT="$repo"   # journal écrit à la racine du dépôt, quel que soit le répertoire courant
ref="${ref_opt:-$(current_branch "$repo")}"; [ -n "$ref" ] || die "HEAD détachée : précisez --ref"
protected="$(cfg brancheProtegee main)"
work="$(mktemp -d "${TMPDIR:-/tmp}/harnais-ci.XXXXXX")"; worktree=""
cleanup() { local c=$?; [ -n "$worktree" ] && git -C "$repo" worktree remove --force "$worktree" >/dev/null 2>&1 || true; rm -rf "$work"; exit "$c"; }
trap cleanup EXIT; trap 'exit 130' INT TERM
checkout_ref "$repo" "$ref" "$work/src" "$mode"
base="$(git -C "$repo" rev-parse --verify --quiet "origin/$protected" || git -C "$repo" rev-parse --verify --quiet "$protected" || echo "$sha")"
# core.quotepath=off : sans lui, Git cite les chemins accentués (« "03_Faisabilit\303\251/…" ») et aucun motif ne s'y applique
changed="$(git -C "$repo" -c core.quotepath=off diff --name-only "$base...$sha" 2>/dev/null || git -C "$repo" -c core.quotepath=off show --name-only --format= "$sha")"
run_code=0; run_docs=0
if [ "$all" = 1 ] || [ -z "$changed" ]; then run_code=1; run_docs=1
else
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if is_docs_only_path "$f"; then run_docs=1; continue; fi
    case "$f" in *.md|.markdownlint-cli2.jsonc|lychee.toml) run_docs=1 ;; *) run_code=1 ;; esac
  done <<EOF2
$changed
EOF2
fi
info "Fichiers modifiés par rapport à $protected : $(printf '%s\n' "$changed" | grep -c . || true)"
code_rc=-; docs_rc=-
if [ "$run_docs" = 1 ] && [ "$(cfg pipeline.docs true)" = true ]; then set +e; "$here/check-docs.sh" "$worktree"; docs_rc=$?; set -e; fi
if [ "$run_code" = 1 ]; then set +e; "$here/build.sh" "$worktree"; code_rc=$?; set -e; fi
label() { case "$1" in -) echo "non concerné" ;; 0) echo "OK" ;; *) echo "ÉCHEC" ;; esac; }
echo; echo "${_b}Pipeline locale — $ref @ ${sha:0:7} ($mode)${_n}"
printf '  %-6s %s\n' code "$(label "$code_rc")" docs "$(label "$docs_rc")"
failed=0; for rc in "$code_rc" "$docs_rc"; do [ "$rc" = - ] || [ "$rc" = 0 ] || failed=1; done
if [ "$failed" = 1 ]; then harnais_event ci ko "$ref@${sha:0:7}"; die "Pipeline en échec : corriger la cause"; fi
harnais_event ci ok "$ref@${sha:0:7} code=$(label "$code_rc") docs=$(label "$docs_rc")"
ok "Pipeline locale verte"
