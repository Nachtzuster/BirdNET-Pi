#!/usr/bin/env bash
# Pre-migration readiness checks for BirdNET-Pibird cutover.
# - Validates local install state (config, DB schema, core services)
# - Probes new host API endpoints
# - Optionally compares old vs new API data when old host exposes /api/*

set -u
set -o pipefail

OLD_URL="${OLD_URL:-http://192.168.1.231}"
NEW_URL="${NEW_URL:-http://192.168.1.78}"
AUTH_USER="${AUTH_USER:-}"
AUTH_PASS="${AUTH_PASS:-}"
TIMEOUT="${TIMEOUT:-10}"
MAX_TOTAL_DIFF="${MAX_TOTAL_DIFF:-25}"
MAX_TODAY_DIFF="${MAX_TODAY_DIFF:-10}"
BIRDNET_DIR="${BIRDNET_DIR:-$HOME/BirdNET-Pi}"
CONFIG_FILE="${CONFIG_FILE:-/etc/birdnet/birdnet.conf}"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
NC="\033[0m"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/pre_migration_check.sh [options]

Options:
  --old-url URL            Old host URL (default: http://192.168.1.231)
  --new-url URL            New host URL (default: http://192.168.1.78)
  --auth-user USER         Basic auth username (optional)
  --auth-pass PASS         Basic auth password (optional)
  --timeout SECONDS        Curl timeout per request (default: 10)
  --max-total-diff N       Warn threshold for total_count diff (default: 25)
  --max-today-diff N       Warn threshold for todays_count diff (default: 10)
  -h, --help               Show this help

Examples:
  ./scripts/pre_migration_check.sh
  ./scripts/pre_migration_check.sh --auth-user birdnet --auth-pass 'secret'
  ./scripts/pre_migration_check.sh --old-url http://pibird.local --new-url http://pibird2.local
EOF
}

normalize_url() {
  local url="$1"
  echo "${url%/}"
}

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo -e "${GREEN}[PASS]${NC} $*"; }
log_warn() { WARN_COUNT=$((WARN_COUNT + 1)); echo -e "${YELLOW}[WARN]${NC} $*"; }
log_fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo -e "${RED}[FAIL]${NC} $*"; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

curl_auth_args=()
if [ -n "$AUTH_USER" ] || [ -n "$AUTH_PASS" ]; then
  curl_auth_args=(-u "${AUTH_USER}:${AUTH_PASS}")
fi

http_code() {
  local url="$1"
  curl -sS -m "$TIMEOUT" "${curl_auth_args[@]}" -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000"
}

fetch_json() {
  local url="$1"
  local outfile="$2"
  curl -sS -m "$TIMEOUT" "${curl_auth_args[@]}" "$url" -o "$outfile" 2>/dev/null
}

json_field() {
  local file="$1"
  local expr="$2"
  jq -r "$expr // empty" "$file" 2>/dev/null
}

check_local_install() {
  log_info "Running local install checks..."

  if [ -f "$CONFIG_FILE" ]; then
    log_pass "Config file exists: $CONFIG_FILE"
  else
    log_fail "Config file missing: $CONFIG_FILE"
  fi

  local db_path="$BIRDNET_DIR/scripts/birds.db"
  if [ -f "$db_path" ]; then
    log_pass "Database exists: $db_path"
  else
    log_fail "Database missing: $db_path"
    return
  fi

  if have_cmd sqlite3; then
    local tbl_count
    tbl_count="$(sqlite3 "$db_path" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='detections';" 2>/dev/null || echo 0)"
    if [ "$tbl_count" = "1" ]; then
      log_pass "detections table exists"
    else
      log_fail "detections table missing"
    fi

    local required_cols
    required_cols="Date Time Sci_Name Com_Name Confidence Lat Lon Cutoff Week Sens Overlap File_Name"
    local col
    for col in $required_cols; do
      if sqlite3 "$db_path" "PRAGMA table_info(detections);" 2>/dev/null | awk -F'|' '{print $2}' | grep -qx "$col"; then
        :
      else
        log_fail "Missing detections column: $col"
      fi
    done
    log_pass "detections schema check completed"

    local total_rows
    total_rows="$(sqlite3 "$db_path" "SELECT COUNT(*) FROM detections;" 2>/dev/null || echo 0)"
    if [ "${total_rows:-0}" -gt 0 ]; then
      log_pass "Detections present in DB: $total_rows rows"
    else
      log_warn "No detections in DB (may be expected for a fresh install)"
    fi
  else
    log_warn "sqlite3 not installed; skipping DB schema checks"
  fi

  if [ -f "$CONFIG_FILE" ]; then
    if grep -q '^CADDY_PWD=' "$CONFIG_FILE"; then
      local pwd_val
      pwd_val="$(grep '^CADDY_PWD=' "$CONFIG_FILE" | tail -n1 | cut -d'=' -f2- | tr -d '"' | xargs)"
      if [ -n "$pwd_val" ]; then
        log_pass "CADDY_PWD is configured"
      else
        log_warn "CADDY_PWD key exists but value is empty"
      fi
    else
      log_warn "CADDY_PWD is not set in $CONFIG_FILE"
    fi
  fi

  if have_cmd systemctl; then
    local must_be_active
    must_be_active="caddy birdnet-web birdnet_analysis birdnet_recording extraction"
    local svc
    for svc in $must_be_active; do
      if systemctl is-active --quiet "$svc"; then
        log_pass "Service active: $svc"
      else
        log_fail "Service not active: $svc"
      fi
    done

    if systemctl is-enabled --quiet birdnet-web 2>/dev/null; then
      log_pass "Service enabled: birdnet-web"
    else
      log_warn "Service not enabled: birdnet-web"
    fi
  else
    log_warn "systemctl not available; skipping service checks"
  fi
}

check_new_host() {
  local base="$1"
  log_info "Running new host checks against $base ..."

  local root_code
  root_code="$(http_code "$base/")"
  if [ "$root_code" = "200" ] || [ "$root_code" = "301" ] || [ "$root_code" = "302" ]; then
    log_pass "New host root reachable ($root_code)"
  else
    log_fail "New host root not reachable ($root_code): $base/"
  fi

  local tmp_health tmp_public tmp_info tmp_stats
  tmp_health="$(mktemp)"
  tmp_public="$(mktemp)"
  tmp_info="$(mktemp)"
  tmp_stats="$(mktemp)"

  if fetch_json "$base/api/health" "$tmp_health"; then
    if have_cmd jq && jq -e . "$tmp_health" >/dev/null 2>&1; then
      local status
      status="$(json_field "$tmp_health" '.status')"
      if [ "$status" = "healthy" ]; then
        log_pass "/api/health status is healthy"
      else
        log_fail "/api/health returned unexpected status: ${status:-<empty>}"
      fi
    else
      log_fail "/api/health did not return valid JSON"
    fi
  else
    log_fail "Failed to fetch /api/health from new host"
  fi

  if fetch_json "$base/api/system/public-status" "$tmp_public"; then
    if have_cmd jq && jq -e . "$tmp_public" >/dev/null 2>&1; then
      local public_state core_active core_total
      public_state="$(json_field "$tmp_public" '.status')"
      core_active="$(json_field "$tmp_public" '.service_summary.core_active')"
      core_total="$(json_field "$tmp_public" '.service_summary.core_total')"
      if [ "$public_state" = "online" ] || [ "$public_state" = "degraded" ]; then
        log_pass "/api/system/public-status OK (${public_state}, core ${core_active}/${core_total})"
      else
        log_fail "/api/system/public-status returned unexpected status: ${public_state:-<empty>}"
      fi
    else
      log_fail "/api/system/public-status did not return valid JSON"
    fi
  else
    log_fail "Failed to fetch /api/system/public-status from new host"
  fi

  if fetch_json "$base/api/info" "$tmp_info"; then
    if have_cmd jq && jq -e . "$tmp_info" >/dev/null 2>&1; then
      local version model git_hash
      version="$(json_field "$tmp_info" '.version')"
      model="$(json_field "$tmp_info" '.model')"
      git_hash="$(json_field "$tmp_info" '.git_hash')"
      log_pass "/api/info reachable (version: ${version:-unknown}, hash: ${git_hash:-unknown}, model: ${model:-unknown})"

      if [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([\-+][0-9A-Za-z\.-]+)?$ ]]; then
        log_pass "/api/info version is semver-like: $version"
      else
        log_warn "/api/info version is not semver-like: ${version:-<empty>}"
      fi

      if [[ "$git_hash" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
        log_pass "/api/info git_hash looks valid"
      else
        log_warn "/api/info git_hash missing/invalid: ${git_hash:-<empty>}"
      fi
    else
      log_fail "/api/info did not return valid JSON"
    fi
  else
    log_fail "Failed to fetch /api/info from new host"
  fi

  if fetch_json "$base/api/detections/stats" "$tmp_stats"; then
    if have_cmd jq && jq -e . "$tmp_stats" >/dev/null 2>&1; then
      local total todays species
      total="$(json_field "$tmp_stats" '.total_count')"
      todays="$(json_field "$tmp_stats" '.todays_count')"
      species="$(json_field "$tmp_stats" '.species_tally')"
      log_pass "/api/detections/stats reachable (total=${total:-?}, today=${todays:-?}, species=${species:-?})"
    else
      log_fail "/api/detections/stats did not return valid JSON"
    fi
  else
    log_fail "Failed to fetch /api/detections/stats from new host"
  fi

  local cfg_code
  cfg_code="$(http_code "$base/api/config")"
  if [ -n "$AUTH_USER" ] || [ -n "$AUTH_PASS" ]; then
    if [ "$cfg_code" = "200" ]; then
      log_pass "/api/config accessible with supplied credentials"
    else
      log_fail "/api/config not accessible with supplied credentials (HTTP $cfg_code)"
    fi
  else
    if [ "$cfg_code" = "401" ] || [ "$cfg_code" = "503" ]; then
      log_pass "/api/config protected as expected (HTTP $cfg_code)"
    elif [ "$cfg_code" = "200" ]; then
      log_warn "/api/config is open without credentials"
    else
      log_warn "/api/config returned unexpected status without credentials (HTTP $cfg_code)"
    fi
  fi

  rm -f "$tmp_health" "$tmp_public" "$tmp_info" "$tmp_stats"
}

abs_diff() {
  local a="$1"
  local b="$2"
  if [ "$a" -ge "$b" ]; then
    echo $((a - b))
  else
    echo $((b - a))
  fi
}

compare_old_new_if_possible() {
  local old_base="$1"
  local new_base="$2"
  log_info "Attempting old vs new API comparison..."

  local old_health_code
  old_health_code="$(http_code "$old_base/api/health")"
  if [ "$old_health_code" != "200" ]; then
    log_warn "Old host does not expose /api/health (HTTP $old_health_code). Skipping API parity checks."
    return
  fi

  if ! have_cmd jq; then
    log_warn "jq missing; skipping JSON parity checks"
    return
  fi

  local old_stats new_stats old_latest new_latest
  old_stats="$(mktemp)"
  new_stats="$(mktemp)"
  old_latest="$(mktemp)"
  new_latest="$(mktemp)"

  if ! fetch_json "$old_base/api/detections/stats" "$old_stats"; then
    log_warn "Could not fetch old /api/detections/stats; skipping parity checks"
    rm -f "$old_stats" "$new_stats" "$old_latest" "$new_latest"
    return
  fi
  if ! fetch_json "$new_base/api/detections/stats" "$new_stats"; then
    log_warn "Could not fetch new /api/detections/stats; skipping parity checks"
    rm -f "$old_stats" "$new_stats" "$old_latest" "$new_latest"
    return
  fi

  local old_total new_total old_today new_today
  old_total="$(json_field "$old_stats" '.total_count')"
  new_total="$(json_field "$new_stats" '.total_count')"
  old_today="$(json_field "$old_stats" '.todays_count')"
  new_today="$(json_field "$new_stats" '.todays_count')"

  if [[ "$old_total" =~ ^[0-9]+$ ]] && [[ "$new_total" =~ ^[0-9]+$ ]]; then
    local total_diff
    total_diff="$(abs_diff "$old_total" "$new_total")"
    if [ "$total_diff" -le "$MAX_TOTAL_DIFF" ]; then
      log_pass "Total detections close enough (old=$old_total, new=$new_total, diff=$total_diff)"
    else
      log_warn "Total detections differ (old=$old_total, new=$new_total, diff=$total_diff)"
    fi
  else
    log_warn "Could not parse total_count for parity check"
  fi

  if [[ "$old_today" =~ ^[0-9]+$ ]] && [[ "$new_today" =~ ^[0-9]+$ ]]; then
    local today_diff
    today_diff="$(abs_diff "$old_today" "$new_today")"
    if [ "$today_diff" -le "$MAX_TODAY_DIFF" ]; then
      log_pass "Today's detections close enough (old=$old_today, new=$new_today, diff=$today_diff)"
    else
      log_warn "Today's detections differ (old=$old_today, new=$new_today, diff=$today_diff)"
    fi
  else
    log_warn "Could not parse todays_count for parity check"
  fi

  if fetch_json "$old_base/api/detections/latest" "$old_latest" && fetch_json "$new_base/api/detections/latest" "$new_latest"; then
    local old_sig new_sig
    old_sig="$(jq -r '[.Date,.Time,.Sci_Name] | @tsv' "$old_latest" 2>/dev/null || true)"
    new_sig="$(jq -r '[.Date,.Time,.Sci_Name] | @tsv' "$new_latest" 2>/dev/null || true)"
    if [ -n "$old_sig" ] && [ -n "$new_sig" ]; then
      if [ "$old_sig" = "$new_sig" ]; then
        log_pass "Latest detection matches between old and new"
      else
        log_warn "Latest detection differs between old and new"
      fi
    fi
  fi

  rm -f "$old_stats" "$new_stats" "$old_latest" "$new_latest"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --old-url)
      OLD_URL="$2"
      shift 2
      ;;
    --new-url)
      NEW_URL="$2"
      shift 2
      ;;
    --auth-user)
      AUTH_USER="$2"
      shift 2
      ;;
    --auth-pass)
      AUTH_PASS="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    --max-total-diff)
      MAX_TOTAL_DIFF="$2"
      shift 2
      ;;
    --max-today-diff)
      MAX_TODAY_DIFF="$2"
      shift 2
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

OLD_URL="$(normalize_url "$OLD_URL")"
NEW_URL="$(normalize_url "$NEW_URL")"

if [ -n "$AUTH_USER" ] || [ -n "$AUTH_PASS" ]; then
  curl_auth_args=(-u "${AUTH_USER}:${AUTH_PASS}")
fi

echo
echo "=============================================="
echo " BirdNET-Pibird Pre-Migration Check"
echo "=============================================="
echo "Old URL: $OLD_URL"
echo "New URL: $NEW_URL"
echo "BIRDNET_DIR: $BIRDNET_DIR"
echo

if ! have_cmd curl; then
  echo "curl is required but not installed." >&2
  exit 2
fi

if ! have_cmd jq; then
  log_warn "jq not installed; JSON-level checks will be limited"
fi

check_local_install
check_new_host "$NEW_URL"
compare_old_new_if_possible "$OLD_URL" "$NEW_URL"

echo
echo "=============================================="
echo "Summary: PASS=$PASS_COUNT WARN=$WARN_COUNT FAIL=$FAIL_COUNT"
echo "=============================================="

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi

exit 0
