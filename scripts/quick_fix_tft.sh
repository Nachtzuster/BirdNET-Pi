#!/usr/bin/env bash
# Quick Fix Script for TFT Display Service
# This script updates the tft_display.py script and ensures Python packages are installed

set -e

echo "=== TFT Display Quick Update Script ==="
echo ""

# Check if running from correct directory
if [ ! -f "scripts/tft_display.py" ]; then
    echo "ERROR: Please run this script from ~/BirdNET-Pi directory"
    echo "Usage: cd ~/BirdNET-Pi && bash scripts/quick_fix_tft.sh"
    exit 1
fi

# Step 1: Copy updated script to /usr/local/bin
echo "Step 1: Installing updated tft_display.py script..."
# Remove existing file/symlink to avoid "same file" error
sudo rm -f /usr/local/bin/tft_display.py
if sudo cp scripts/tft_display.py /usr/local/bin/tft_display.py; then
    sudo chmod +x /usr/local/bin/tft_display.py
    echo "  ✓ Script installed to /usr/local/bin/tft_display.py"
else
    echo "  ✗ Failed to install script"
    exit 1
fi

# Step 2: Check if virtual environment exists
echo ""
echo "Step 2: Checking Python virtual environment..."
if [ -d "birdnet/bin" ]; then
    echo "  ✓ Virtual environment found"
else
    echo "  ✗ Virtual environment not found at ~/BirdNET-Pi/birdnet"
    echo "  Please install BirdNET-Pi first"
    exit 1
fi

# Step 3: Install/update Python packages in virtual environment
echo ""
echo "Step 3: Installing Python packages in virtual environment..."
source birdnet/bin/activate

echo "  Installing luma.lcd..."
pip install --upgrade "luma.lcd>=2.11.0" 2>&1 | grep -E "(Requirement already satisfied|Successfully installed|Collecting)" || true

echo "  Installing luma.core..."
pip install --upgrade "luma.core>=2.4.0" 2>&1 | grep -E "(Requirement already satisfied|Successfully installed|Collecting)" || true

echo "  Installing Pillow (compatible with streamlit)..."
pip install --upgrade "Pillow>=11.0,<12.0" 2>&1 | grep -E "(Requirement already satisfied|Successfully installed|Collecting)" || true

# Verify packages are importable
echo ""
echo "  Verifying packages..."
if python -c "import luma.lcd; import luma.core; import PIL; print('All packages OK')" 2>/dev/null; then
    echo "  ✓ All Python packages verified"
else
    echo "  ✗ Package verification failed"
    deactivate
    exit 1
fi

deactivate

# Step 4: Restart service
echo ""
echo "Step 4: Restarting tft_display.service..."
sudo systemctl daemon-reload
sudo systemctl restart tft_display.service

# Wait a moment for service to start
sleep 2

# Step 5: Check service status
echo ""
echo "Step 5: Checking service status..."
if sudo systemctl is-active --quiet tft_display.service; then
    echo "  ✓ Service is running"
else
    echo "  ⚠ Service is not running"
    echo ""
    echo "Showing last 20 log lines:"
    sudo journalctl -u tft_display.service -n 20 --no-pager
fi

echo ""
echo "=== Update Complete ==="
echo ""
echo "To monitor logs in real-time:"
echo "  sudo journalctl -u tft_display.service -f"
echo ""
echo "To check service status:"
echo "  sudo systemctl status tft_display.service"
echo ""
