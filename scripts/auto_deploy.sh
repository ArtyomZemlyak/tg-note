#!/usr/bin/env bash
set -Eeuo pipefail

# Auto-deploy script for cron/systemd timers.
# - Detects remote changes in a Git repo
# - Blocks deploy if critical files changed (configurable)
# - Builds Docker images from specified compose file(s)
# - Restarts/updates services via docker compose
#
# Usage:
#   scripts/auto_deploy.sh -c /path/to/auto_deploy.conf
#   Or configure via env vars; see below.

# -------- Defaults (can be overridden by config/env) --------
CONFIG_FILE="${CONFIG_FILE:-}"
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILES="${COMPOSE_FILES:-docker-compose.yml}"  # colon-separated for multiple: file1.yml:file2.yml
SERVICES="${SERVICES:-}"  # optional space-separated list of services
BUILD_FLAGS="${BUILD_FLAGS:---pull}"  # e.g. "--pull" or "--pull --no-cache"
DEPLOY_COMMAND="${DEPLOY_COMMAND:-up}"  # up | restart
UP_FLAGS="${UP_FLAGS:--d --remove-orphans}"  # flags used when DEPLOY_COMMAND=up
PRUNE_AFTER="${PRUNE_AFTER:-false}"  # true|false
AUTO_CHECKOUT="${AUTO_CHECKOUT:-false}"  # true|false
LOG_FILE="${LOG_FILE:-$REPO_DIR/logs/auto_deploy.log}"
LOCK_FILE="${LOCK_FILE:-$REPO_DIR/logs/auto_deploy.lock}"
CRITICAL_PATHS_FILE="${CRITICAL_PATHS_FILE:-$REPO_DIR/scripts/auto_deploy.blocklist}"
CRITICAL_PATHS="${CRITICAL_PATHS:-}"  # comma-separated glob patterns
COMPOSE_CMD_OVERRIDE="${COMPOSE_CMD_OVERRIDE:-}"  # e.g. "docker-compose"

# -------- Options --------
usage() {
  cat <<USAGE
Auto-deploy script

Options:
  -c <file>   Path to config file to source (bash format)
  -h          Show this help

Exit codes:
  0: no changes or deploy succeeded
 10: critical change detected, deploy skipped
  1: error
USAGE
}

while getopts ":c:h" opt; do
  case "$opt" in
    c) CONFIG_FILE="$OPTARG" ;;
    h) usage; exit 0 ;;
    :) echo "Option -$OPTARG requires an argument" >&2; exit 1 ;;
    \?) echo "Unknown option -$OPTARG" >&2; exit 1 ;;
  esac
done

# Load config if provided
if [[ -n "$CONFIG_FILE" ]]; then
  if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
  else
    echo "Config file not found: $CONFIG_FILE" >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S%z')] $*" | tee -a "$LOG_FILE"; }

# Prevent overlapping runs
exec {LOCK_FD}>"$LOCK_FILE" || { echo "Cannot open lock file: $LOCK_FILE" >&2; exit 1; }
if ! flock -n "$LOCK_FD"; then
  log "Another instance is running. Exiting."
  exit 0
fi

# Detect docker compose command
compose_cmd() {
  if [[ -n "$COMPOSE_CMD_OVERRIDE" ]]; then
    echo "$COMPOSE_CMD_OVERRIDE"
    return
  fi
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""  # not found
  fi
}

COMPOSE_BIN="$(compose_cmd)"
if [[ -z "$COMPOSE_BIN" ]]; then
  log "docker compose not found (need 'docker compose' or 'docker-compose')"
  exit 1
fi

# Validate repo
if ! git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  log "Not a git repository: $REPO_DIR"
  exit 1
fi

# Ensure we are on desired branch
current_branch="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "$BRANCH" ]]; then
  if [[ "$AUTO_CHECKOUT" == "true" ]]; then
    log "Checking out branch $BRANCH (was $current_branch)"
    git -C "$REPO_DIR" checkout "$BRANCH"
  else
    log "Current branch is $current_branch, expected $BRANCH. Set AUTO_CHECKOUT=true to switch automatically."
    exit 1
  fi
fi

# Ensure working tree is clean
if [[ -n "$(git -C "$REPO_DIR" status --porcelain)" ]]; then
  log "Working tree not clean. Aborting."
  exit 1
fi

log "Fetching updates from $REMOTE/$BRANCH"
# Prune and fetch the specific branch
if ! git -C "$REPO_DIR" fetch "$REMOTE" "$BRANCH" --prune; then
  log "git fetch failed"
  exit 1
fi

upstream_ref="$REMOTE/$BRANCH"

# Check divergence
base_commit="$(git -C "$REPO_DIR" merge-base HEAD "$upstream_ref")"
ahead_count="$(git -C "$REPO_DIR" rev-list --left-only --count HEAD..."$upstream_ref")"
behind_count="$(git -C "$REPO_DIR" rev-list --right-only --count HEAD..."$upstream_ref")"

if (( ahead_count > 0 )); then
  log "Local branch is ahead of $upstream_ref by $ahead_count commits. Aborting (manual intervention required)."
  exit 1
fi

# Compute changed files
mapfile -t changed_files < <(git -C "$REPO_DIR" diff --name-only HEAD.."$upstream_ref")
if (( ${#changed_files[@]} == 0 )); then
  log "No changes detected."
  exit 0
fi

log "Changed files since HEAD..$upstream_ref:"
for f in "${changed_files[@]}"; do log "  - $f"; done

# Build pattern list
read_critical_patterns() {
  local patterns=()
  if [[ -n "$CRITICAL_PATHS" ]]; then
    IFS=',' read -r -a list <<<"$CRITICAL_PATHS"
    for p in "${list[@]}"; do
      [[ -n "$p" ]] && patterns+=("$p")
    done
  fi
  if [[ -f "$CRITICAL_PATHS_FILE" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" || "$line" =~ ^\s*# ]] && continue
      patterns+=("$line")
    done < "$CRITICAL_PATHS_FILE"
  fi
  if (( ${#patterns[@]} == 0 )); then
    # Sensible defaults
    patterns=(
      ".env*"
      "config/**"
      "docker-compose*.yml"
      "Dockerfile*"
      "pyproject.toml"
      "poetry.lock"
      "requirements*.txt"
      "scripts/auto_deploy*"
      "config.example.yaml"
    )
  fi
  printf '%s\n' "${patterns[@]}"
}

mapfile -t critical_patterns < <(read_critical_patterns)

shopt -s globstar extglob dotglob

critical_hit=""
for f in "${changed_files[@]}"; do
  for pat in "${critical_patterns[@]}"; do
    # shellcheck disable=SC2254
    case "$f" in
      $pat)
        critical_hit="$f"; break ;;
    esac
  done
  [[ -n "$critical_hit" ]] && break
fi

if [[ -n "$critical_hit" ]]; then
  log "Critical change detected ($critical_hit). Deploy blocked."
  exit 10
fi

log "Pulling latest changes..."
if ! git -C "$REPO_DIR" pull --ff-only "$REMOTE" "$BRANCH"; then
  log "git pull failed (non-fast-forward?)"
  exit 1
fi

# Build images
compose_flags=()
IFS=':' read -r -a compose_array <<<"$COMPOSE_FILES"
for cf in "${compose_array[@]}"; do
  if [[ -f "$REPO_DIR/$cf" ]]; then
    compose_flags+=( -f "$REPO_DIR/$cf" )
  else
    log "Compose file not found: $REPO_DIR/$cf"; exit 1
  fi
done

log "Building images via: $COMPOSE_BIN ${compose_flags[*]} build $BUILD_FLAGS ${SERVICES:-<all>}"
# shellcheck disable=SC2086
$COMPOSE_BIN "${compose_flags[@]}" build $BUILD_FLAGS ${SERVICES:-}

# Deploy
if [[ "$DEPLOY_COMMAND" == "restart" ]]; then
  log "Ensuring services are up-to-date (up ${UP_FLAGS}) before restart..."
  # shellcheck disable=SC2086
  $COMPOSE_BIN "${compose_flags[@]}" up ${UP_FLAGS} ${SERVICES:-}
  log "Restarting services..."
  # shellcheck disable=SC2086
  $COMPOSE_BIN "${compose_flags[@]}" restart ${SERVICES:-}
else
  log "Deploying (up ${UP_FLAGS})..."
  # shellcheck disable=SC2086
  $COMPOSE_BIN "${compose_flags[@]}" up ${UP_FLAGS} ${SERVICES:-}
fi

if [[ "$PRUNE_AFTER" == "true" ]]; then
  log "Pruning dangling images..."
  docker image prune -f || true
fi

log "Deployment completed successfully."
exit 0
