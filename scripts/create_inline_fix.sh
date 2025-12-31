#!/usr/bin/env bash
# INLINE FIX - Paste this entire script into terminal and run it
# This fixes the TFT display copy error without needing git

cat > /tmp/fix_tft_copy.sh << 'HEREDOC_EOF'
#!/usr/bin/env bash
set -e

echo "=== Direct TFT Copy Fix ==="
echo "This will fix the copy error using a temporary file method"
echo ""

# Check we're in the right place
if [ ! -f "scripts/tft_display.py" ]; then
    echo "ERROR: Run this from ~/BirdNET-Pi directory"
    exit 1
fi

echo "Step 1: Copying tft_display.py to /usr/local/bin using temp file method..."

# Create temporary file
TEMP_FILE=$(mktemp)
echo "  → Created temp file: $TEMP_FILE"

# Copy to temp file
if ! cp scripts/tft_display.py "$TEMP_FILE"; then
    rm -f "$TEMP_FILE" 2>/dev/null || true
    echo "  ✗ Failed to copy to temp file"
    exit 1
fi
echo "  ✓ Copied to temp file"

# Move temp file to destination (works even if destination is symlink)
if ! sudo mv -f "$TEMP_FILE" /usr/local/bin/tft_display.py; then
    rm -f "$TEMP_FILE" 2>/dev/null || true
    echo "  ✗ Failed to move to /usr/local/bin"
    exit 1
fi
echo "  ✓ Moved to /usr/local/bin/tft_display.py"

# Set permissions
sudo chmod +x /usr/local/bin/tft_display.py
echo "  ✓ Set executable permissions"

echo ""
echo "SUCCESS! Script installed."
echo ""

# Verify
if [ -f "/usr/local/bin/tft_display.py" ]; then
    echo "Verification:"
    ls -la /usr/local/bin/tft_display.py
fi

echo ""
echo "Now installing Python packages..."
echo ""

if [ ! -d "birdnet/bin" ]; then
    echo "WARNING: Virtual environment not found"
    echo "Skipping Python package installation"
else
    source birdnet/bin/activate
    pip install --upgrade luma.lcd luma.core Pillow 2>&1 | grep -E "(Requirement|Successfully|Collecting)" || true
    deactivate
    echo "✓ Python packages installed"
fi

echo ""
echo "Restarting service..."
if sudo systemctl restart tft_display.service; then
    echo "✓ Service restarted"
    sudo systemctl status tft_display.service --no-pager | head -10
else
    echo "✗ Failed to restart service"
fi

echo ""
echo "========================================="
echo "Fix complete!"
echo "========================================="
HEREDOC_EOF

chmod +x /tmp/fix_tft_copy.sh

echo "Fix script created at /tmp/fix_tft_copy.sh"
echo ""
echo "Now run:"
echo "  cd ~/BirdNET-Pi"
echo "  bash /tmp/fix_tft_copy.sh"
