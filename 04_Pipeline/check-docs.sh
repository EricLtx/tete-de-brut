#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Contrôles de la documentation (canon harnais-pipeline) : markdownlint-cli2 sur tous les .md, liens par lychee
# sur les .md suivis par Git. Configuration : .markdownlint-cli2.jsonc et lychee.toml à la racine.
#   04_Pipeline/check-docs.sh [racine]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/lib/common.sh"
root="$(cd "${1:-$here/..}" && pwd)"; cd "$root"
need git; need npx "Node.js"
step "Lint Markdown (markdownlint-cli2)"
npx --yes markdownlint-cli2 "**/*.md" || die "markdownlint : documentation non conforme"
step "Liens (lychee)"
files=(); while IFS= read -r f; do files+=("$f"); done < <(git -c core.quotepath=off ls-files -- '*.md')   # chemins accentués lus tels quels
[ "${#files[@]}" -gt 0 ] || die "Aucun fichier Markdown suivi par Git"
if [ -f lychee.toml ]; then lychee_run --config lychee.toml --no-progress "${files[@]}" || die "lychee : liens cassés"
else lychee_run --no-progress --offline "${files[@]}" || die "lychee : liens cassés"; fi
ok "Documentation OK (markdownlint + liens)"
