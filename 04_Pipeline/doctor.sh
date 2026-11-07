#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
# Vérifie que le poste et le dépôt ont ce qu'il faut pour le harnais, et dit ce qui manque.
#   04_Pipeline/doctor.sh
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/lib/common.sh"
root="$(git -C "$here" rev-parse --show-toplevel)"
missing=0
row() { if [ "$3" = ok ]; then printf '  %s✓%s %-16s %s\n' "$_g" "$_n" "$1" "$2"; else printf '  %s✗%s %-16s %s — %s\n' "$_r" "$_n" "$1" "$2" "$4"; missing=1; fi; }
has() { command -v "$1" >/dev/null 2>&1 && echo ok || echo ko; }
step "Outils"
row git "dépôt" "$(has git)" "installer Git"
row python "lecture de config/harnais.json" "$(has python)" "installer Python 3"
row node "markdownlint (npx)" "$(has npx)" "installer Node.js"
if command -v lychee >/dev/null 2>&1 || have_docker; then row lychee "liens (local ou Docker)" ok; else row lychee "liens" ko "installer lychee ou lancer Docker Desktop"; fi
step "Harnais"
[ -f "$root/config/harnais.json" ] && row config "config/harnais.json" ok || row config "config/harnais.json" ko "lancer le skill harnais-pipeline (équiper)"
[ "$(git -C "$root" config core.hooksPath)" = "04_Pipeline/hooks" ] && row hooks "gardes git actives" ok || row hooks "gardes git" ko "git config core.hooksPath 04_Pipeline/hooks"
for h in pre-commit commit-msg pre-merge-commit pre-push; do [ -x "$root/04_Pipeline/hooks/$h" ] && row "$h" "garde" ok || row "$h" "garde" ko "manquante : équiper"; done
[ -d "$root/vault/mandats" ] && row vault "mandats et revues" ok || row vault "mandats et revues" ko "équiper"
[ -f "$root/01_Docs/00_Index/registre-decisions.md" ] && row registres "registres de documentation" ok || row registres "registres" ko "équiper"
echo; [ "$missing" = 0 ] && ok "Poste et dépôt prêts" || { warn "Éléments manquants : voir ci-dessus"; exit 1; }
