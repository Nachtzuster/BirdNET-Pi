#!/usr/bin/env bash
# Update TFT Display Script
# This script ensures /usr/local/bin/tft_display.py is up-to-date with the repository version

set -e

# Get the home directory
if [ -f /etc/birdnet/birdnet.conf ]; then
    source /etc/birdnet/birdnet.conf
    USER=${USER:-$(whoami)}
    HOME=${HOME:-$(eval echo ~$USER)}
else
    USER=$(whoami)
    HOME=$(eval echo ~$USER)
fi

REPO_SCRIPT="$HOME/BirdNET-Pi/scripts/tft_display.py"
TARGET_SCRIPT="/usr/local/bin/tft_display.py"

# Check if repository script exists
if [ ! -f "$REPO_SCRIPT" ]; then
    echo "ERROR: Repository script not found at $REPO_SCRIPT"
    exit 1
fi

# Update the script in /usr/local/bin
echo "Updating TFT display script..."
TEMP_FILE=$(mktemp)

# Copy to temp file first
if ! cp "$REPO_SCRIPT" "$TEMP_FILE"; then
    rm -f "$TEMP_FILE" 2>/dev/null || true
    echo "ERROR: Failed to copy script to temporary file"
    exit 1
fi

# Move to final location with sudo
if ! sudo mv -f "$TEMP_FILE" "$TARGET_SCRIPT"; then
    rm -f "$TEMP_FILE" 2>/dev/null || true
    echo "ERROR: Failed to move script to $TARGET_SCRIPT"
    exit 1
fi

# Set execute permission
if ! sudo chmod +x "$TARGET_SCRIPT"; then
    echo "ERROR: Failed to set execute permission"
    exit 1
fi

echo "TFT display script updated successfully"
exit 0
