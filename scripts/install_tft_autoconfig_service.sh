#!/usr/bin/env bash
# Install TFT Auto-Configuration Service
# This service runs at boot to automatically detect and configure TFT displays

set -e

USER=${USER:-$(whoami)}
HOME=${HOME:-$(eval echo ~$USER)}

echo "Installing TFT auto-configuration service..."

# Create the systemd service file
cat << EOF | sudo tee /usr/lib/systemd/system/tft_autoconfig.service > /dev/null
[Unit]
Description=BirdNET-Pi TFT Auto-Configuration Service
After=network.target
Before=tft_display.service
DefaultDependencies=no

[Service]
Type=oneshot
User=root
ExecStart=/bin/bash ${HOME}/BirdNET-Pi/scripts/auto_configure_tft.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable the service
sudo systemctl enable tft_autoconfig.service

echo "✓ TFT auto-configuration service installed and enabled"
echo "  The service will run at boot to automatically detect and configure TFT displays"
echo ""
echo "To run it manually: sudo systemctl start tft_autoconfig.service"
echo "To check status: sudo systemctl status tft_autoconfig.service"
echo "To view logs: sudo journalctl -u tft_autoconfig.service"
