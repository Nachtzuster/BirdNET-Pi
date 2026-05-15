#!/usr/bin/env bash
# Compatibility wrapper for the consolidated installer.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "BirdNET-Pi now uses a single installer entry point."
echo "Forwarding to ${SCRIPT_DIR}/install_web.sh ..."

exec "${SCRIPT_DIR}/install_web.sh" "$@"
