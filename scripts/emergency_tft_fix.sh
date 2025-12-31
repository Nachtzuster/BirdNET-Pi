#!/usr/bin/env bash
# Emergency Fix Script for TFT Display Copy Error
# This script can be run standalone to fix the copy error without git merge
# Download and run with: curl -o /tmp/emergency_tft_fix.sh <URL> && bash /tmp/emergency_tft_fix.sh

set -e

echo "=== Emergency TFT Display Fix ==="
echo ""
echo "This script will fix the 'same file' copy error by using a temporary file approach."
echo ""

# Check if running from correct directory
if [ ! -f "scripts/tft_display.py" ]; then
    echo "ERROR: Please run this script from ~/BirdNET-Pi directory"
    echo "Usage: cd ~/BirdNET-Pi && bash /tmp/emergency_tft_fix.sh"
    exit 1
fi

# Verify the files exist
if [ ! -f "scripts/tft_display.py" ]; then
    echo "ERROR: scripts/tft_display.py not found"
    exit 1
fi

echo "Step 1: Installing tft_display.py to /usr/local/bin using temporary file method..."
echo ""

# Create temporary file with secure permissions
TEMP_FILE=$(mktemp)
echo "  → Created temporary file: $TEMP_FILE"

# Copy source to temp file
if ! cp scripts/tft_display.py "$TEMP_FILE"; then
    rm -f "$TEMP_FILE" 2>/dev/null || true
    echo "  ✗ ERROR: Failed to copy scripts/tft_display.py to temporary file"
    exit 1
fi
echo "  ✓ Copied scripts/tft_display.py to temporary file"

# Move temp file to destination (this works even if destination is a symlink)
if ! sudo mv -f "$TEMP_FILE" /usr/local/bin/tft_display.py; then
    rm -f "$TEMP_FILE" 2>/dev/null || true
    echo "  ✗ ERROR: Failed to move temporary file to /usr/local/bin/tft_display.py"
    exit 1
fi
echo "  ✓ Moved temporary file to /usr/local/bin/tft_display.py"

# Set executable permissions
if ! sudo chmod +x /usr/local/bin/tft_display.py; then
    echo "  ✗ ERROR: Failed to set executable permission"
    exit 1
fi
echo "  ✓ Set executable permissions"

echo ""
echo "SUCCESS! Script installed to /usr/local/bin/tft_display.py"
echo ""

# Verify installation
if [ -f "/usr/local/bin/tft_display.py" ]; then
    echo "Verification:"
    ls -la /usr/local/bin/tft_display.py
    echo ""
fi

# Now install Python packages
echo "Step 2: Installing Python packages..."
echo ""

if [ ! -d "birdnet/bin" ]; then
    echo "  ✗ ERROR: Virtual environment not found at ~/BirdNET-Pi/birdnet"
    echo "  Please install BirdNET-Pi first"
    exit 1
fi

echo "  → Activating virtual environment..."
source birdnet/bin/activate

echo "  → Installing luma.lcd..."
pip install --upgrade "luma.lcd>=2.11.0" 2>&1 | grep -E "(Requirement already satisfied|Successfully installed|Collecting)" || true

echo "  → Installing luma.core..."
pip install --upgrade "luma.core>=2.4.0" 2>&1 | grep -E "(Requirement already satisfied|Successfully installed|Collecting)" || true

echo "  → Installing Pillow..."
pip install --upgrade "Pillow>=11.0,<12.0" 2>&1 | grep -E "(Requirement already satisfied|Successfully installed|Collecting)" || true

deactivate
echo "  ✓ Python packages installed"

echo ""
echo "Step 3: Restarting tft_display service..."
echo ""

if sudo systemctl restart tft_display.service; then
    echo "  ✓ Service restarted"
else
    echo "  ✗ WARNING: Failed to restart service"
    echo "  Try manually: sudo systemctl restart tft_display.service"
fi

echo ""
echo "Step 4: Checking service status..."
echo ""

if sudo systemctl is-active --quiet tft_display.service; then
    echo "  ✓ Service is running"
    sudo systemctl status tft_display.service --no-pager | head -15
else
    echo "  ⚠ Service is not running"
    echo ""
    echo "Check logs with:"
    echo "  sudo journalctl -u tft_display.service -n 50 --no-pager"
fi

echo ""
echo "========================================="
echo "Fix completed!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Check service status: sudo systemctl status tft_display.service"
echo "2. View logs: sudo journalctl -u tft_display.service -f"
echo "3. If you still see exit code 1, see: docs/TFT_EXIT_CODE_1_FIX_NL.md"
echo ""
