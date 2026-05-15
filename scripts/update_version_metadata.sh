#!/usr/bin/env bash
# Update versions.md with current git metadata for release/build workflows.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSIONS_FILE="${VERSIONS_FILE:-$ROOT_DIR/versions.md}"

SERVICE_VERSION=""
API_VERSION=""
GIT_HASH=""
GIT_BRANCH=""
BUILD_DATE_UTC=""
CHANGELOG_FILE=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/update_version_metadata.sh [options]

Options:
  --service-version X.Y.Z   Set service_version (SemVer recommended)
  --api-version X.Y.Z       Set api_version
  --git-hash HASH           Override git_hash (default: current HEAD short hash)
  --git-branch BRANCH       Override git_branch (default: current branch)
  --build-date-utc ISO8601  Override build_date_utc (default: current UTC timestamp)
  --changelog-file FILE     Override changelog_file (default: existing value or version.md)
  --file PATH               Path to versions.md (default: repo root versions.md)
  -h, --help                Show this help

Examples:
  ./scripts/update_version_metadata.sh
  ./scripts/update_version_metadata.sh --service-version 0.14.0
  ./scripts/update_version_metadata.sh --service-version 0.14.0 --api-version 1.1.0
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --service-version)
      SERVICE_VERSION="${2:-}"
      shift 2
      ;;
    --api-version)
      API_VERSION="${2:-}"
      shift 2
      ;;
    --git-hash)
      GIT_HASH="${2:-}"
      shift 2
      ;;
    --git-branch)
      GIT_BRANCH="${2:-}"
      shift 2
      ;;
    --build-date-utc)
      BUILD_DATE_UTC="${2:-}"
      shift 2
      ;;
    --changelog-file)
      CHANGELOG_FILE="${2:-}"
      shift 2
      ;;
    --file)
      VERSIONS_FILE="${2:-}"
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

if ! command -v git >/dev/null 2>&1; then
  echo "git is required." >&2
  exit 2
fi

if [ -z "$GIT_HASH" ]; then
  GIT_HASH="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
fi
if [ -z "$GIT_BRANCH" ]; then
  GIT_BRANCH="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD)"
fi
if [ -z "$BUILD_DATE_UTC" ]; then
  BUILD_DATE_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
fi

mkdir -p "$(dirname "$VERSIONS_FILE")"
if [ ! -f "$VERSIONS_FILE" ]; then
  cat > "$VERSIONS_FILE" <<'EOF'
# BirdNET-Pibird Release Metadata
# Format: key: value
# This file is machine-read by the API for concise version display.

service_version: unknown
git_hash: unknown
git_branch: unknown
api_version: 1.0.0
build_date_utc: unknown
changelog_file: version.md
EOF
fi

tmp_file="$(mktemp)"
cp "$VERSIONS_FILE" "$tmp_file"

set_key() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}:" "$tmp_file"; then
    sed -i.bak "s|^${key}:.*|${key}: ${value}|" "$tmp_file"
    rm -f "${tmp_file}.bak"
  else
    printf "%s: %s\n" "$key" "$value" >> "$tmp_file"
  fi
}

set_key "git_hash" "$GIT_HASH"
set_key "git_branch" "$GIT_BRANCH"
set_key "build_date_utc" "$BUILD_DATE_UTC"

if [ -n "$SERVICE_VERSION" ]; then
  set_key "service_version" "$SERVICE_VERSION"
fi
if [ -n "$API_VERSION" ]; then
  set_key "api_version" "$API_VERSION"
fi
if [ -n "$CHANGELOG_FILE" ]; then
  set_key "changelog_file" "$CHANGELOG_FILE"
fi

mv "$tmp_file" "$VERSIONS_FILE"

echo "Updated $VERSIONS_FILE"
echo "  service_version: $(awk -F': ' '/^service_version:/{print $2}' "$VERSIONS_FILE")"
echo "  git_hash:        $(awk -F': ' '/^git_hash:/{print $2}' "$VERSIONS_FILE")"
echo "  git_branch:      $(awk -F': ' '/^git_branch:/{print $2}' "$VERSIONS_FILE")"
echo "  api_version:     $(awk -F': ' '/^api_version:/{print $2}' "$VERSIONS_FILE")"
echo "  build_date_utc:  $(awk -F': ' '/^build_date_utc:/{print $2}' "$VERSIONS_FILE")"
