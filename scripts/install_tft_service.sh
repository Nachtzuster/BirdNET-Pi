#!/usr/bin/env bash
# Web-safe TFT Service Installation Wrapper
# This script is called from the web interface to install TFT display support

set -e

# Get the home directory and config
if [ -f /etc/birdnet/birdnet.conf ]; then
    source /etc/birdnet/birdnet.conf
    USER=${USER:-$(whoami)}
    HOME=${HOME:-$(eval echo ~$USER)}
else
    USER=$(whoami)
    HOME=$(eval echo ~$USER)
fi

SCRIPT_DIR="$HOME/BirdNET-Pi/scripts"
LOG_FILE="/tmp/tft_install_$(date +%Y%m%d_%H%M%S).log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== TFT Display Service Installation ==="
log "User: $USER"
log "Home: $HOME"
log ""

# Check if install_tft.sh exists
if [ ! -f "$SCRIPT_DIR/install_tft.sh" ]; then
    log "ERROR: install_tft.sh not found at $SCRIPT_DIR/install_tft.sh"
    echo "ERROR: Installation script not found. Please check your BirdNET-Pi installation."
    exit 1
fi

# Check if TFT service is already installed
if [ -f "/usr/lib/systemd/system/tft_display.service" ]; then
    log "INFO: TFT display service already installed"
    echo "TFT display service is already installed."
    exit 0
fi

log "Installing TFT display service..."
echo "Installing TFT display service. This will create the service but not enable it."
echo ""

# Install the TFT display service (function from install_services.sh)
install_tft_display_service() {
    log "Creating TFT display service file..."
    
    # Get Python virtual environment path
    PYTHON_VIRTUAL_ENV="$HOME/BirdNET-Pi/birdnet/bin/python3"
    
    if [ ! -f "$PYTHON_VIRTUAL_ENV" ]; then
        log "WARNING: Python virtual environment not found, using system python3"
        PYTHON_VIRTUAL_ENV="/usr/bin/python3"
    fi
    
    # Create service file
    cat << EOF > $HOME/BirdNET-Pi/templates/tft_display.service
[Unit]
Description=BirdNET-Pi TFT Display Service
After=birdnet_analysis.service
[Service]
Restart=on-failure
RestartSec=10
Type=simple
User=$USER
ExecStart=$PYTHON_VIRTUAL_ENV /usr/local/bin/tft_display.py
[Install]
WantedBy=multi-user.target
EOF

    # Create symlink to systemd
    log "Creating systemd symlink..."
    sudo ln -sf $HOME/BirdNET-Pi/templates/tft_display.service /usr/lib/systemd/system/
    
    # Reload systemd
    log "Reloading systemd daemon..."
    sudo systemctl daemon-reload
    
    log "TFT display service installed successfully!"
}

# Run the installation
if install_tft_display_service; then
    log "=== Installation Complete ==="
    echo ""
    echo "✓ TFT Display service has been installed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. If you have a TFT display connected, run: ~/BirdNET-Pi/scripts/install_tft.sh"
    echo "   to configure the hardware settings (SPI, display type, rotation, etc.)"
    echo ""
    echo "2. To enable the service: sudo systemctl enable --now tft_display.service"
    echo ""
    echo "3. The service will start automatically after hardware configuration."
    echo ""
    echo "Note: The service is now available but NOT enabled. This is intentional"
    echo "      so you can configure your TFT hardware first."
    echo ""
    log "Log file saved to: $LOG_FILE"
    exit 0
else
    log "ERROR: Installation failed"
    echo "ERROR: Installation failed. Please check the log at: $LOG_FILE"
    exit 1
fi
