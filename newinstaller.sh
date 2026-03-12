#!/usr/bin/env bash
# BirdNET-Pibird Installer
#
# Usage:
#   curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | bash
#
# To install from the development branch explicitly:
#   curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | RELEASE_CHANNEL=edge BRANCH=BRANCH_NAME bash
#
# Example (feature branch):
#   curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | RELEASE_CHANNEL=edge BRANCH=fastapi-svelte-migration-mk1 bash

set -e

# Configuration - can be overridden via environment variables
REPO_URL="${REPO_URL:-https://github.com/cpieper/BirdNET-Pibird.git}"
BRANCH="${BRANCH:-fastapi-svelte-migration-mk1}"
INSTALL_DIR="${INSTALL_DIR:-${HOME}/BirdNET-Pi}"
RELEASE_CHANNEL="${RELEASE_CHANNEL:-}"
INSTALL_REF=""
INSTALL_REF_TYPE=""

latest_matching_tag() {
  local include_prerelease="${1}"
  local tags
  tags="$(
    git ls-remote --refs --tags "${REPO_URL}" \
      | awk '{print $2}' \
      | sed 's#refs/tags/##' \
      | grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$' \
      | sort -V -r
  )"

  if [ "${include_prerelease}" != "1" ]; then
    tags="$(printf '%s\n' "${tags}" | grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+(\+[0-9A-Za-z.-]+)?$' || true)"
  fi

  printf '%s\n' "${tags}" | head -n 1
}

remote_branch_exists() {
  git ls-remote --exit-code --heads "${REPO_URL}" "$1" > /dev/null 2>&1
}

confirm_nonstable_channel() {
  [ "${RELEASE_CHANNEL}" = "stable" ] && return 0

  echo ""
  echo "Selected non-stable channel: ${RELEASE_CHANNEL}"
  echo "This is an explicit opt-in path and may include unfinished or breaking changes."
  if [ -t 0 ]; then
    printf "Continue with ${RELEASE_CHANNEL}? [y/N]: "
    read -r nonstable_reply
    case "${nonstable_reply:-N}" in
      y|Y|yes|YES) ;;
      *)
        echo "Installation cancelled."
        exit 1
        ;;
    esac
  else
    echo "Non-interactive install requires explicit RELEASE_CHANNEL=${RELEASE_CHANNEL}; proceeding."
  fi
}

resolve_install_target() {
  case "${RELEASE_CHANNEL}" in
    stable)
      INSTALL_REF="$(latest_matching_tag 0)"
      INSTALL_REF_TYPE="tag"
      [ -n "${INSTALL_REF}" ] || {
        echo "No stable release tags were found in ${REPO_URL}."
        exit 1
      }
      ;;
    prerelease)
      INSTALL_REF="$(latest_matching_tag 1)"
      INSTALL_REF_TYPE="tag"
      [ -n "${INSTALL_REF}" ] || {
        echo "No prerelease or stable release tags were found in ${REPO_URL}."
        exit 1
      }
      ;;
    edge)
      INSTALL_REF="${BRANCH}"
      INSTALL_REF_TYPE="branch"
      remote_branch_exists "${INSTALL_REF}" || {
        echo "Branch '${INSTALL_REF}' was not found in ${REPO_URL}."
        exit 1
      }
      ;;
  esac
}

validate_release_channel() {
  case "${1}" in
    stable|prerelease|edge) return 0 ;;
    *) return 1 ;;
  esac
}

prompt_release_channel() {
  echo "Select release channel:"
  echo "  1) stable"
  echo "  2) prerelease"
  echo "  3) edge"
  printf "Choice [1]: "
  read -r channel_choice
  case "${channel_choice:-1}" in
    1) RELEASE_CHANNEL="stable" ;;
    2) RELEASE_CHANNEL="prerelease" ;;
    3) RELEASE_CHANNEL="edge" ;;
    *)
      echo "Invalid selection, defaulting to stable."
      RELEASE_CHANNEL="stable"
      ;;
  esac
}

if [ -z "${RELEASE_CHANNEL}" ]; then
  if [ -t 0 ]; then
    prompt_release_channel
  else
    RELEASE_CHANNEL="stable"
  fi
fi

if ! validate_release_channel "${RELEASE_CHANNEL}"; then
  echo "Unsupported RELEASE_CHANNEL='${RELEASE_CHANNEL}'. Use stable, prerelease, or edge."
  exit 1
fi

echo ""
echo "=============================================="
echo "   BirdNET-Pibird Installer"
echo "=============================================="
echo ""
echo "Repository: ${REPO_URL}"
echo "Channel:    ${RELEASE_CHANNEL}"
if [ "${RELEASE_CHANNEL}" = "edge" ]; then
  echo "Branch:     ${BRANCH}"
fi
echo "Install to: ${INSTALL_DIR}"
echo ""

if [ "$EUID" == 0 ]
  then echo "Please run as a non-root user."
  exit 1
fi

if [ "$(uname -m)" != "aarch64" ] && [ "$(uname -m)" != "x86_64" ];then
  echo "BirdNET-Pi requires a 64-bit OS.
It looks like your operating system is using $(uname -m),
but would need to be aarch64 or x86_64."
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
if [ "${PY_VERSION}" == "39" ] ;then
  echo "### BirdNET-Pi requires a newer OS. Bullseye is deprecated, please use Bookworm. ###"
  [ -z "${FORCE_BULLSEYE}" ] && exit 1
fi

# we require passwordless sudo
sudo -K
if ! sudo -n true; then
    echo "Passwordless sudo is not working. Aborting"
    exit 1
fi

# Simple new installer
HOME=$HOME
USER=$USER

export HOME=$HOME
export USER=$USER
export RELEASE_CHANNEL="${RELEASE_CHANNEL}"

PACKAGES_MISSING=
for cmd in git jq ; do
  if ! which $cmd &> /dev/null;then
      PACKAGES_MISSING="${PACKAGES_MISSING} $cmd"
  fi
done
if [[ ! -z $PACKAGES_MISSING ]] ; then
  sudo apt update
  sudo apt -y install $PACKAGES_MISSING
fi

confirm_nonstable_channel
resolve_install_target

echo "Resolved install target: ${INSTALL_REF} (${INSTALL_REF_TYPE})"
if [ "${RELEASE_CHANNEL}" != "edge" ] && [ -n "${BRANCH}" ] && [ "${BRANCH}" != "fastapi-svelte-migration-mk1" ]; then
  echo "Note: BRANCH is ignored for ${RELEASE_CHANNEL} installs unless RELEASE_CHANNEL=edge is selected."
fi

# Clone the repository
echo "Cloning ${REPO_URL} (${INSTALL_REF_TYPE}: ${INSTALL_REF})..."
git clone --branch "${INSTALL_REF}" --depth=1 "${REPO_URL}" "${INSTALL_DIR}" &&

# Legacy installer scripts assume ~/BirdNET-Pi. Keep that path valid.
if [ "${INSTALL_DIR}" != "${HOME}/BirdNET-Pi" ]; then
  echo "Linking ${HOME}/BirdNET-Pi -> ${INSTALL_DIR} for installer compatibility..."
  ln -sfn "${INSTALL_DIR}" "${HOME}/BirdNET-Pi"
fi

# Set SKIP_PHP to use new web interface instead of PHP
export SKIP_PHP=1

# Export BIRDNET_DIR for scripts that need it
export BIRDNET_DIR="${INSTALL_DIR}"

# Run base installation
"${INSTALL_DIR}/scripts/install_birdnet.sh"
if [ ${PIPESTATUS[0]} -ne 0 ];then
  echo "The base installation exited unsuccessfully."
  exit 1
fi

# Install new web interface (FastAPI + SvelteKit)
echo ""
echo "=============================================="
echo "Installing modern web interface..."
echo "=============================================="
echo ""

"${INSTALL_DIR}/scripts/install_web.sh"
if [ ${PIPESTATUS[0]} -eq 0 ];then
  echo ""
  echo "=============================================="
  echo "Installation completed successfully!"
  echo "=============================================="
  echo ""
  echo "The system will reboot in 10 seconds..."
  echo "Press Ctrl+C to cancel reboot"
  sleep 10
  sudo reboot
else
  echo "The web interface installation exited unsuccessfully."
  echo "You can try running it manually: ${INSTALL_DIR}/scripts/install_web.sh"
  exit 1
fi
