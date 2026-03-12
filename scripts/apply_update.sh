#!/usr/bin/env bash
# Apply a BirdNET-Pibird software update for a selected release channel.

set -euo pipefail

if [ -z "${BIRDNET_APPLY_UPDATE_STAGE2:-}" ]; then
  export BIRDNET_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  export BIRDNET_APPLY_UPDATE_STAGE2=1
  tmp_script="$(mktemp /tmp/birdnet-apply-update.XXXXXX.sh)"
  cp "${BASH_SOURCE[0]}" "$tmp_script"
  chmod +x "$tmp_script"
  exec "$tmp_script" "$@"
fi

usage() {
  cat <<'EOF'
Usage:
  ./scripts/apply_update.sh [options]

Options:
  --channel stable|prerelease|edge  Update channel to apply (default: stable)
  --target REF                      Override target tag or branch
  --branch NAME                     Edge branch to follow (default: current tracked branch)
  --remote NAME                     Git remote to fetch from (default: origin)
  --skip-backup                     Do not create a backup before applying update
  -h, --help                        Show this help
EOF
}

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

sanitize_value() {
  printf '%s' "${1:-}" | tr '\n' ' ' | sed -E 's/[[:space:]]+/ /g'
}

write_status() {
  mkdir -p "$STATE_DIR"
  cat > "$STATUS_FILE" <<EOF
status: $(sanitize_value "$STATUS")
stage: $(sanitize_value "$STAGE")
channel: $(sanitize_value "$CHANNEL")
target: $(sanitize_value "$TARGET")
target_type: $(sanitize_value "$TARGET_TYPE")
message: $(sanitize_value "$MESSAGE")
started_at: $(sanitize_value "$STARTED_AT")
updated_at: $(timestamp_utc)
pid: $$
previous_ref: $(sanitize_value "$PREVIOUS_REF")
current_ref: $(sanitize_value "$CURRENT_REF")
backup_created: $(sanitize_value "$BACKUP_CREATED")
backup_path: $(sanitize_value "$BACKUP_PATH")
error: $(sanitize_value "$ERROR_MESSAGE")
EOF
}

set_stage() {
  STAGE="$1"
  MESSAGE="$2"
  write_status
  echo "[$(timestamp_utc)] [$STAGE] $MESSAGE"
}

fail_update() {
  ERROR_MESSAGE="${1:-Unknown update failure}"
  STATUS="failed"
  MESSAGE="Update failed"
  write_status
  echo "[$(timestamp_utc)] [failed] $ERROR_MESSAGE" >&2
  exit 1
}

validate_channel() {
  case "$1" in
    stable|prerelease|edge)
      ;;
    *)
      fail_update "Invalid channel '$1'. Expected stable, prerelease, or edge."
      ;;
  esac
}

resolve_home() {
  getent passwd "$1" | cut -d: -f6
}

resolve_stable_tag() {
  git -C "$BASE_DIR" tag --list --sort=-version:refname \
    | grep -E '^[vV]?[0-9]+\.[0-9]+\.[0-9]+(\+[0-9A-Za-z.-]+)?$' \
    | head -n 1
}

resolve_prerelease_tag() {
  git -C "$BASE_DIR" tag --list --sort=-version:refname \
    | grep -E '^[vV]?[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$' \
    | head -n 1
}

resolve_edge_branch() {
  if [ -n "$EDGE_BRANCH" ]; then
    printf '%s\n' "$EDGE_BRANCH"
    return
  fi

  local current_branch
  current_branch="$(git -C "$BASE_DIR" branch --show-current 2>/dev/null || true)"
  if [ -n "$current_branch" ]; then
    printf '%s\n' "$current_branch"
    return
  fi

  if [ -f "$BASE_DIR/versions.md" ]; then
    local metadata_branch
    metadata_branch="$(awk -F': ' '/^git_branch:/{print $2}' "$BASE_DIR/versions.md" | tail -n 1)"
    if [ -n "$metadata_branch" ] && [ "$metadata_branch" != "unknown" ] && [ "$metadata_branch" != "HEAD" ] && [ "${metadata_branch#tag:}" = "$metadata_branch" ]; then
      printf '%s\n' "$metadata_branch"
      return
    fi
  fi

  printf 'main\n'
}

ensure_clean_checkout() {
  if [ -n "$(git -C "$BASE_DIR" status --porcelain --untracked-files=no)" ]; then
    fail_update "Refusing to update a repository with local tracked changes."
  fi
}

refresh_remote_refs() {
  git -C "$BASE_DIR" fetch --tags --prune "$REMOTE"
  if [ "$CHANNEL" = "edge" ] || [ -n "$EDGE_BRANCH" ]; then
    local branch_ref
    branch_ref="$(resolve_edge_branch)"
    git -C "$BASE_DIR" fetch --prune "$REMOTE" "${branch_ref}:refs/remotes/${REMOTE}/${branch_ref}"
  fi
}

create_backup() {
  [ "$SKIP_BACKUP" = "1" ] && return

  mkdir -p "$BACKUP_DIR"
  BACKUP_PATH="$BACKUP_DIR/birdnet-backup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
  set_stage "backup" "Creating pre-update backup at $BACKUP_PATH"
  "$BASE_DIR/scripts/backup_data.sh" -a backup -f "$BACKUP_PATH"
  BACKUP_CREATED="true"
  write_status
}

checkout_target() {
  PREVIOUS_REF="$(git -C "$BASE_DIR" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"

  case "$CHANNEL" in
    stable)
      TARGET_TYPE="tag"
      if [ -z "$TARGET" ]; then
        TARGET="$(resolve_stable_tag)"
      fi
      [ -n "$TARGET" ] || fail_update "No stable release tag was found."
      set_stage "checkout" "Checking out stable release $TARGET"
      git -C "$BASE_DIR" checkout --detach "$TARGET"
      ;;
    prerelease)
      TARGET_TYPE="tag"
      if [ -z "$TARGET" ]; then
        TARGET="$(resolve_prerelease_tag)"
      fi
      [ -n "$TARGET" ] || fail_update "No prerelease tag was found."
      set_stage "checkout" "Checking out prerelease $TARGET"
      git -C "$BASE_DIR" checkout --detach "$TARGET"
      ;;
    edge)
      TARGET_TYPE="branch"
      TARGET="${TARGET:-$(resolve_edge_branch)}"
      [ -n "$TARGET" ] || fail_update "No edge branch could be resolved."
      set_stage "checkout" "Checking out edge branch $TARGET"
      if git -C "$BASE_DIR" show-ref --verify --quiet "refs/heads/$TARGET"; then
        git -C "$BASE_DIR" switch "$TARGET"
      else
        git -C "$BASE_DIR" switch -c "$TARGET" --track "$REMOTE/$TARGET"
      fi
      git -C "$BASE_DIR" reset --hard "$REMOTE/$TARGET"
      ;;
  esac

  CURRENT_REF="$(git -C "$BASE_DIR" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
  write_status
}

install_backend_deps() {
  local pip_cmd="$BASE_DIR/birdnet/bin/pip"
  [ -x "$pip_cmd" ] || pip_cmd="$BASE_DIR/birdnet/bin/pip3"
  [ -x "$pip_cmd" ] || fail_update "Python virtualenv pip executable not found."
  [ -f "$BASE_DIR/backend/requirements.txt" ] || fail_update "backend/requirements.txt not found."

  set_stage "backend" "Installing backend Python dependencies"
  "$pip_cmd" install -q -r "$BASE_DIR/backend/requirements.txt"
}

build_frontend() {
  [ -d "$BASE_DIR/frontend" ] || fail_update "frontend directory not found."

  set_stage "frontend" "Installing frontend dependencies and building assets"
  cd "$BASE_DIR/frontend"
  if [ -f package-lock.json ]; then
    npm ci --silent
  else
    npm install
  fi
  npm run build
}

run_host_updates() {
  set_stage "migrations" "Running host update snippets"
  sudo "$BASE_DIR/scripts/update_birdnet_snippets.sh"

  set_stage "metadata" "Refreshing version metadata"
  local branch_value
  branch_value="$(git -C "$BASE_DIR" rev-parse --abbrev-ref HEAD)"
  if [ "$branch_value" = "HEAD" ] && [ "$TARGET_TYPE" = "tag" ]; then
    branch_value="tag:$TARGET"
  fi
  "$BASE_DIR/scripts/update_version_metadata.sh" \
    --git-hash "$CURRENT_REF" \
    --git-branch "$branch_value"
}

restart_services() {
  set_stage "restart" "Reloading services"
  sudo systemctl daemon-reload
  sudo ln -sf "$BASE_DIR"/scripts/* /usr/local/bin/
  sudo systemctl restart birdnet-web
  sudo "$BASE_DIR/scripts/restart_services.sh"
}

verify_update() {
  set_stage "verify" "Verifying updated services"
  if ! sudo systemctl is-active --quiet birdnet-web; then
    fail_update "birdnet-web did not become active after restart."
  fi
}

cleanup() {
  local exit_code=$?
  rm -rf "$LOCK_DIR"
  if [ "$exit_code" -ne 0 ] && [ "$STATUS" != "failed" ]; then
    ERROR_MESSAGE="apply_update.sh exited with code $exit_code"
    STATUS="failed"
    MESSAGE="Update failed"
    write_status
  fi
}

CHANNEL="stable"
TARGET=""
TARGET_TYPE=""
EDGE_BRANCH=""
REMOTE="origin"
SKIP_BACKUP="0"
STATUS="running"
STAGE="starting"
MESSAGE="Preparing update"
STARTED_AT="$(timestamp_utc)"
PREVIOUS_REF=""
CURRENT_REF=""
BACKUP_CREATED="false"
BACKUP_PATH=""
ERROR_MESSAGE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --channel)
      CHANNEL="${2:-}"
      shift 2
      ;;
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --branch)
      EDGE_BRANCH="${2:-}"
      shift 2
      ;;
    --remote)
      REMOTE="${2:-}"
      shift 2
      ;;
    --skip-backup)
      SKIP_BACKUP="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

validate_channel "$CHANNEL"

if [ -f /etc/birdnet/birdnet.conf ]; then
  # shellcheck disable=SC1091
  source /etc/birdnet/birdnet.conf
fi

RUN_USER="${BIRDNET_USER:-${USER:-$(id -un)}}"
USER_HOME="$(resolve_home "$RUN_USER")"
if [ -z "$USER_HOME" ]; then
  USER_HOME="${HOME:-/home/$RUN_USER}"
fi

BASE_DIR="${BIRDNET_REPO_DIR:-$USER_HOME/BirdNET-Pi}"
STATE_DIR="${BASE_DIR}/.update-state"
STATUS_FILE="${STATE_DIR}/status"
LOG_FILE="${STATE_DIR}/apply-update.log"
LOCK_DIR="${STATE_DIR}/lock"
BACKUP_DIR="${STATE_DIR}/backups"

mkdir -p "$STATE_DIR"

if [ -d "$LOCK_DIR" ]; then
  existing_pid="$(awk -F': ' '/^pid:/{print $2}' "$STATUS_FILE" 2>/dev/null || true)"
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    fail_update "Another update process is already running (PID $existing_pid)."
  fi
  rm -rf "$LOCK_DIR"
fi

mkdir -p "$LOCK_DIR"
: > "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

trap cleanup EXIT

write_status
set_stage "preflight" "Running update preflight checks"

[ -d "$BASE_DIR/.git" ] || fail_update "Git repository not found at $BASE_DIR."
[ -x "$BASE_DIR/scripts/backup_data.sh" ] || fail_update "backup_data.sh is missing or not executable."
[ -x "$BASE_DIR/scripts/update_birdnet_snippets.sh" ] || fail_update "update_birdnet_snippets.sh is missing or not executable."
[ -x "$BASE_DIR/scripts/update_version_metadata.sh" ] || fail_update "update_version_metadata.sh is missing or not executable."
[ -x "$BASE_DIR/birdnet/bin/python3" ] || fail_update "BirdNET Python environment is not installed."
[ -f "$BASE_DIR/package.json" ] || true
command -v git >/dev/null 2>&1 || fail_update "git is required."
command -v npm >/dev/null 2>&1 || fail_update "npm is required."

ensure_clean_checkout
create_backup

set_stage "fetch" "Fetching latest repository metadata from $REMOTE"
refresh_remote_refs

checkout_target
install_backend_deps
build_frontend
run_host_updates
restart_services
verify_update

STATUS="completed"
STAGE="completed"
MESSAGE="Update completed successfully"
write_status

