# Fonctions partagées par les scripts de 04_Pipeline (bash 3.2+ : Git Bash, macOS, Linux).
# Canon harnais-pipeline : ne pas modifier ici, adapter dans lib/local.sh si besoin.

if [ -t 1 ]; then _b=$'\033[1m'; _y=$'\033[33m'; _r=$'\033[31m'; _g=$'\033[32m'; _n=$'\033[0m'; else _b=; _y=; _r=; _g=; _n=; fi

step() { printf '\n%s▶ %s%s\n' "$_b" "$*" "$_n"; }
info() { printf '  %s\n' "$*"; }
ok()   { printf '%s✓ %s%s\n' "$_g" "$*" "$_n"; }
warn() { printf '%s⚠ %s%s\n' "$_y" "$*" "$_n" >&2; }
die()  { printf '%s✗ %s%s\n' "$_r" "$*" "$_n" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "Outil manquant : $1${2:+ ($2)}"; }

have_docker() { command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; }
is_windows() { case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; *) return 1 ;; esac; }
host_path() { (cd "$1" && { pwd -W 2>/dev/null || pwd; }); }

# Vérification des liens : lychee local, sinon conteneur lycheeverse/lychee.
lychee_run() {
  if command -v lychee >/dev/null 2>&1; then lychee "$@"
  elif have_docker; then MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path .):/input" -w /input lycheeverse/lychee "$@"
  else die "lychee introuvable : installer lychee ou lancer Docker Desktop"; fi
}

current_branch() { git -C "$1" symbolic-ref --quiet --short HEAD || true; }

# Extrait un état précis du dépôt dans un worktree temporaire : jamais la copie de travail.
# Usage : checkout_ref <dépôt> <branche> <dossier> [local|origin]   → définit sha, subject, worktree.
checkout_ref() {
  local repo_dir="$1" ref="$2" dest="$3" mode="${4:-origin}"
  if [ "$mode" = local ]; then
    step "Extraction du dernier commit local de $ref"
    sha="$(git -C "$repo_dir" rev-parse --verify --quiet "$ref^{commit}")" || die "Branche locale « $ref » introuvable"
    [ -z "$(git -C "$repo_dir" status --porcelain)" ] || warn "Modifications non commitées : elles ne sont pas contrôlées (seul le dernier commit l'est)"
  else
    step "Récupération de origin/$ref"
    git -C "$repo_dir" fetch --quiet origin "$ref" || die "Branche « $ref » introuvable sur origin : poussez-la d'abord"
    sha="$(git -C "$repo_dir" rev-parse FETCH_HEAD)"
  fi
  subject="$(git -C "$repo_dir" log -1 --format=%s "$sha")"
  info "$ref @ ${sha:0:7} — $subject"
  worktree="$dest"
  git -C "$repo_dir" worktree add --quiet --detach "$worktree" "$sha"
}

# Lecture de config/harnais.json (python, présent sur tous les postes équipés). Usage : cfg <clé.sous-clé> [défaut]
cfg() {
  local root; root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  local f="$root/config/harnais.json"
  [ -f "$f" ] || { printf '%s' "${2:-}"; return 0; }
  # Une config présente mais illisible (python absent, JSON cassé) arrête la garde : ne jamais retomber en silence
  # sur un défaut permissif (sans cela, « interdits » vide laissait passer un .pem).
  command -v python >/dev/null 2>&1 || die "python introuvable : impossible de lire config/harnais.json, dont dépendent les gardes du harnais"
  local out err; err="$(mktemp)"
  out="$(python - "$f" "$1" "${2:-}" <<'PY' 2>"$err"
import json, sys
sys.stdout.reconfigure(newline="", encoding="utf-8")
d = json.load(open(sys.argv[1], encoding="utf-8"))
for k in sys.argv[2].split("."):
    d = d[k] if isinstance(d, dict) and k in d else None
    if d is None: break
if d is None: print(sys.argv[3], end="")
elif isinstance(d, list): print("\n".join(map(str, d)), end="")
elif isinstance(d, bool): print("true" if d else "false", end="")
else: print(d, end="")
PY
)" || die "config/harnais.json illisible (clé $1) : $(tr -d '\r' < "$err" | tail -3 | paste -sd' ' -)"
  rm -f "$err"
  printf '%s' "$out"
}
