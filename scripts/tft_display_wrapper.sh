#!/usr/bin/env bash
# TFT Display Service Wrapper
# This script ensures the TFT display script is up-to-date before starting the service

set -e

# Get the home directory
if [ -f /etc/birdnet/birdnet.conf ]; then
    # shellcheck source=/dev/null
    source /etc/birdnet/birdnet.conf
    USER=${USER:-$(whoami)}
    HOME=${HOME:-$(eval echo ~"$USER")}
else
    USER=$(whoami)
    HOME=$(eval echo ~"$USER")
fi

REPO_SCRIPT="$HOME/BirdNET-Pi/scripts/tft_display.py"
TARGET_SCRIPT="/usr/local/bin/tft_display.py"
PYTHON_VENV="$HOME/BirdNET-Pi/birdnet/bin/python3"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Check if repository script exists
if [ ! -f "$REPO_SCRIPT" ]; then
    log_message "ERROR: Repository script not found at $REPO_SCRIPT"
    exit 1
fi

# Check if target script exists, if not or if repo version is newer, update it
update_needed=false

if [ ! -f "$TARGET_SCRIPT" ]; then
    log_message "Target script $TARGET_SCRIPT not found, will install it"
    update_needed=true
elif [ "$REPO_SCRIPT" -nt "$TARGET_SCRIPT" ]; then
    log_message "Repository script is newer than target script, will update"
    update_needed=true
fi

if [ "$update_needed" = true ]; then
    log_message "Updating TFT display script from repository..."
    TEMP_FILE=$(mktemp -t tft_display.XXXXXX)
    
    # Copy to temp file first
    if ! cp "$REPO_SCRIPT" "$TEMP_FILE"; then
        rm -f "$TEMP_FILE" 2>/dev/null || true
        log_message "ERROR: Failed to copy script to temporary file"
        exit 1
    fi
    
    # Move to final location with sudo
    if ! sudo mv -f "$TEMP_FILE" "$TARGET_SCRIPT"; then
        rm -f "$TEMP_FILE" 2>/dev/null || true
        log_message "ERROR: Failed to move script to $TARGET_SCRIPT"
        exit 1
    fi
    
    # Set read and execute permissions for all users
    if ! sudo chmod 755 "$TARGET_SCRIPT"; then
        log_message "ERROR: Failed to set permissions"
        exit 1
    fi
    
    log_message "TFT display script updated successfully"
fi

# Determine which Python to use
if [ -f "$PYTHON_VENV" ]; then
    PYTHON="$PYTHON_VENV"
    log_message "Using Python from virtual environment: $PYTHON"
else
    PYTHON="/usr/bin/python3"
    log_message "Virtual environment not found, using system Python: $PYTHON"
fi

# Check if Python exists
if [ ! -f "$PYTHON" ]; then
    log_message "ERROR: Python interpreter not found at $PYTHON"
    exit 1
fi

# Start the TFT display script
log_message "Starting TFT display service..."
exec "$PYTHON" "$TARGET_SCRIPT"
