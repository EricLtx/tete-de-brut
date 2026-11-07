# Journal machine du harnais : une ligne JSON par événement dans vault/runtime/events.jsonl (hors Git).
# Usage : harnais_event <genre> <état> [détail]      genres : ci, build, docs, deploy, mandat, doublage, merge, push, commit
# Pourquoi : l'orchestrateur et les hooks lisent ce journal pour savoir où en est chaque mandat sans relire le chat.
harnais_event() {
  # HARNAIS_ROOT (posé par ci.sh et les gardes) : la racine du dépôt, même si le script tourne depuis un sous-dossier
  # ou un worktree temporaire ; sinon la racine du répertoire courant.
  local root; root="${HARNAIS_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local f="$root/vault/runtime/events.jsonl"
  [ -d "$root/vault" ] || return 0
  mkdir -p "$(dirname "$f")"
  local br sha at d
  br="$(git -C "$root" symbolic-ref --quiet --short HEAD 2>/dev/null || echo detached)"
  sha="$(git -C "$root" rev-parse --short HEAD 2>/dev/null || echo -)"
  at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  d="${3:-}"; d="${d//\\/\\\\}"; d="${d//\"/\\\"}"; d="${d//$'\n'/ }"; d="${d//$'\r'/}"
  printf '{"at":"%s","genre":"%s","etat":"%s","branche":"%s","commit":"%s","detail":"%s"}\n' "$at" "$1" "$2" "$br" "$sha" "$d" >> "$f"
}
