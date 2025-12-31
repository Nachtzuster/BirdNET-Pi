#!/usr/bin/env bash
# Fix Pillow version conflict with streamlit
# This script downgrades Pillow to version compatible with streamlit

set -e

echo "=== Pillow Version Fix for Streamlit Compatibility ==="
echo ""

cd ~/BirdNET-Pi 2>/dev/null || cd /home/*/BirdNET-Pi || { echo "ERROR: Cannot find BirdNET-Pi directory"; exit 1; }

if [ ! -d "birdnet/bin" ]; then
    echo "ERROR: Virtual environment not found"
    exit 1
fi

echo "Current Pillow version:"
source birdnet/bin/activate
pip show Pillow | grep Version || echo "Pillow not installed"
echo ""

echo "Streamlit requires: Pillow<12,>=7.1.0"
echo "Installing compatible Pillow version..."
echo ""

# Install Pillow with version constraint compatible with streamlit
pip install "Pillow>=11.0,<12.0"

echo ""
echo "New Pillow version:"
pip show Pillow | grep Version
echo ""

# Verify streamlit is happy
echo "Verifying streamlit dependency..."
if pip check 2>&1 | grep -i pillow; then
    echo "WARNING: There may still be dependency issues"
else
    echo "✓ No dependency conflicts detected"
fi

deactivate

echo ""
echo "========================================="
echo "Fix complete!"
echo "========================================="
echo ""
echo "Pillow has been downgraded to version 11.x which is compatible with streamlit."
echo ""
