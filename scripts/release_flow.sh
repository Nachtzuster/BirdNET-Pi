#!/usr/bin/env bash
# Guided release flow for BirdNET-Pibird tags/metadata.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="origin"
TAG=""
BRANCH=""
COMMIT_MSG=""
API_VERSION=""
YES="false"
RUN_CHECKS="true"
CREATE_GH_RELEASE="false"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/release_flow.sh --tag vX.Y.Z[-rcN] [options]

Options:
  --tag TAG               Release tag, e.g. v0.14.0-rc6 (required)
  --branch BRANCH         Branch to push (default: current branch)
  --remote REMOTE         Git remote (default: origin)
  --api-version X.Y.Z     Optional api_version for versions.md
  --commit-msg MSG        Commit message if there are local changes
                          (default: chore(release): TAG)
  --no-checks             Skip frontend/backend verification
  --gh-release            Create GitHub release with gh CLI after push
  -y, --yes               Non-interactive mode (auto-confirm)
  -h, --help              Show this help

Flow:
  1) Run checks (optional)
  2) Update versions.md via update_version_metadata.sh
  3) Commit local changes (if any)
  4) Create annotated tag
  5) Push branch, then push tag
  6) Optionally create GitHub release (gh CLI)
EOF
}

confirm() {
  local prompt="$1"
  if [[ "$YES" == "true" ]]; then
    return 0
  fi
  read -r -p "$prompt [y/N]: " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]]
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      TAG="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --remote)
      REMOTE="${2:-}"
      shift 2
      ;;
    --api-version)
      API_VERSION="${2:-}"
      shift 2
      ;;
    --commit-msg)
      COMMIT_MSG="${2:-}"
      shift 2
      ;;
    --no-checks)
      RUN_CHECKS="false"
      shift
      ;;
    --gh-release)
      CREATE_GH_RELEASE="true"
      shift
      ;;
    -y|--yes)
      YES="true"
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

if [[ -z "$TAG" ]]; then
  echo "Error: --tag is required." >&2
  usage
  exit 2
fi

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.]+)?$ ]]; then
  echo "Error: tag '$TAG' does not look like a release tag (expected vX.Y.Z or vX.Y.Z-rcN)." >&2
  exit 2
fi

SERVICE_VERSION="${TAG#v}"

if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is required." >&2
  exit 2
fi

if ! git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: not inside a git repository." >&2
  exit 2
fi

CURRENT_BRANCH="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" == "HEAD" ]]; then
  echo "Error: detached HEAD detected. Switch to a branch before releasing." >&2
  exit 2
fi

if [[ -z "$BRANCH" ]]; then
  BRANCH="$CURRENT_BRANCH"
fi
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "Error: current branch is '$CURRENT_BRANCH', but --branch '$BRANCH' was requested." >&2
  exit 2
fi

if git -C "$ROOT_DIR" rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: local tag '$TAG' already exists." >&2
  exit 2
fi

if git -C "$ROOT_DIR" ls-remote --exit-code --tags "$REMOTE" "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "Error: remote tag '$TAG' already exists on '$REMOTE'." >&2
  exit 2
fi

echo "== Release Flow =="
echo "Repo:           $ROOT_DIR"
echo "Branch:         $BRANCH"
echo "Remote:         $REMOTE"
echo "Tag:            $TAG"
echo "Service version:$SERVICE_VERSION"
echo

if [[ "$RUN_CHECKS" == "true" ]]; then
  echo "[1/6] Running checks..."
  (
    cd "$ROOT_DIR/frontend"
    npm run check
  )
  (
    cd "$ROOT_DIR"
    python3 -m compileall backend/app >/dev/null
  )
else
  echo "[1/6] Checks skipped (--no-checks)."
fi

echo "[2/6] Updating versions.md..."
UPDATE_ARGS=(--service-version "$SERVICE_VERSION")
if [[ -n "$API_VERSION" ]]; then
  UPDATE_ARGS+=(--api-version "$API_VERSION")
fi
"$ROOT_DIR/scripts/update_version_metadata.sh" "${UPDATE_ARGS[@]}"

if [[ -z "$COMMIT_MSG" ]]; then
  COMMIT_MSG="chore(release): ${TAG}"
fi

echo "[3/6] Reviewing and committing local changes (if any)..."
if [[ -n "$(git -C "$ROOT_DIR" status --porcelain)" ]]; then
  git -C "$ROOT_DIR" status --short
  if ! confirm "Commit all current changes with message: '$COMMIT_MSG'?"; then
    echo "Aborted before commit."
    exit 1
  fi
  git -C "$ROOT_DIR" add -A
  git -C "$ROOT_DIR" commit -m "$COMMIT_MSG"
else
  echo "Working tree clean; no commit needed."
fi

RELEASE_COMMIT="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
echo "Release commit: $RELEASE_COMMIT"

echo "[4/6] Creating annotated tag..."
git -C "$ROOT_DIR" tag -a "$TAG" -m "Release $TAG"

echo "[5/6] Pushing branch and tag..."
git -C "$ROOT_DIR" push "$REMOTE" "$BRANCH"
git -C "$ROOT_DIR" push "$REMOTE" "$TAG"

echo "[6/6] Final verification..."
git -C "$ROOT_DIR" show --no-patch --oneline "$TAG"
echo "Release flow completed for $TAG."

if [[ "$CREATE_GH_RELEASE" == "true" ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    echo "gh CLI not found; skipping GitHub release creation."
    exit 0
  fi
  if confirm "Create GitHub release for $TAG now?"; then
    (
      cd "$ROOT_DIR"
      gh release create "$TAG" --verify-tag --generate-notes
    )
    echo "GitHub release created for $TAG."
  fi
fi

