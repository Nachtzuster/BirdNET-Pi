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
    
    # Install the tft_display.py script to /usr/local/bin
    log "Installing tft_display.py script to /usr/local/bin..."
    if [ -f "$HOME/BirdNET-Pi/scripts/tft_display.py" ]; then
        # Use a temporary file to avoid "same file" error when destination is a symlink
        TEMP_FILE=$(mktemp)
        if ! cp "$HOME/BirdNET-Pi/scripts/tft_display.py" "$TEMP_FILE"; then
            rm -f "$TEMP_FILE" 2>/dev/null || true
            log "ERROR: Failed to copy tft_display.py to temporary file"
            return 1
        fi
        if ! sudo mv -f "$TEMP_FILE" /usr/local/bin/tft_display.py; then
            rm -f "$TEMP_FILE" 2>/dev/null || true
            log "ERROR: Failed to move tft_display.py to /usr/local/bin"
            return 1
        fi
        if ! sudo chmod +x /usr/local/bin/tft_display.py; then
            log "ERROR: Failed to set execute permission on /usr/local/bin/tft_display.py"
            return 1
        fi
        log "tft_display.py installed successfully"
    else
        log "ERROR: tft_display.py not found at $HOME/BirdNET-Pi/scripts/tft_display.py"
        return 1
    fi
    
    # Install the wrapper script to /usr/local/bin
    log "Installing tft_display_wrapper.sh script to /usr/local/bin..."
    if [ -f "$HOME/BirdNET-Pi/scripts/tft_display_wrapper.sh" ]; then
        TEMP_FILE=$(mktemp)
        if ! cp "$HOME/BirdNET-Pi/scripts/tft_display_wrapper.sh" "$TEMP_FILE"; then
            rm -f "$TEMP_FILE" 2>/dev/null || true
            log "ERROR: Failed to copy tft_display_wrapper.sh to temporary file"
            return 1
        fi
        if ! sudo mv -f "$TEMP_FILE" /usr/local/bin/tft_display_wrapper.sh; then
            rm -f "$TEMP_FILE" 2>/dev/null || true
            log "ERROR: Failed to move tft_display_wrapper.sh to /usr/local/bin"
            return 1
        fi
        if ! sudo chmod +x /usr/local/bin/tft_display_wrapper.sh; then
            log "ERROR: Failed to set execute permission on /usr/local/bin/tft_display_wrapper.sh"
            return 1
        fi
        log "tft_display_wrapper.sh installed successfully"
    else
        log "ERROR: tft_display_wrapper.sh not found at $HOME/BirdNET-Pi/scripts/tft_display_wrapper.sh"
        return 1
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
ExecStart=/usr/local/bin/tft_display_wrapper.sh
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
    
    # Install auto-configuration service
    log "Installing TFT auto-configuration service..."
    if [ -f "$SCRIPT_DIR/install_tft_autoconfig_service.sh" ]; then
        bash "$SCRIPT_DIR/install_tft_autoconfig_service.sh" || log "Auto-config service installation completed with warnings"
    fi
}

# Run the installation
if install_tft_display_service; then
    log "=== Installation Complete ==="
    echo ""
    echo "✓ TFT Display service has been installed successfully!"
    echo ""
    
    # Check if hardware is already configured (SPI/TFT overlays in config.txt)
    NEEDS_REBOOT=false
    CONFIG_FILE="/boot/firmware/config.txt"
    
    if [ -f "$CONFIG_FILE" ]; then
        # Use single grep with multiple patterns for better performance
        if grep -qE "dtoverlay=(spi|tft|ili9341|st7735|st7789|ads7846|xpt2046)" "$CONFIG_FILE"; then
            
            log "INFO: TFT hardware configuration detected in $CONFIG_FILE"
            NEEDS_REBOOT=true
            
            # Run auto-configuration to detect and set up TFT properly
            log "Running automatic TFT configuration..."
            if [ -f "$SCRIPT_DIR/auto_configure_tft.sh" ]; then
                bash "$SCRIPT_DIR/auto_configure_tft.sh" || log "Auto-configuration completed with warnings"
            fi
            
            echo "======================================================="
            echo "⚠️  REBOOT REQUIRED TO ACTIVATE TFT DISPLAY"
            echo "======================================================="
            echo ""
            echo "TFT hardware configuration detected in your system."
            echo "A reboot is NECESSARY to activate the TFT display."
            echo ""
            echo "How to reboot:"
            echo "  • Web interface: Tools -> System Controls -> Reboot"
            echo "  • Command line: sudo reboot"
            echo ""
        fi
    fi
    
    if [ "$NEEDS_REBOOT" = false ]; then
        log "No reboot required for service installation"
        echo "✓ No reboot required."
        echo ""
    fi
    
    echo "Next steps:"
    if [ "$NEEDS_REBOOT" = true ]; then
        echo "1. ⚠️  REBOOT the system NOW (required for TFT hardware)"
        echo "2. After reboot, enable the service:"
        echo "   sudo systemctl enable --now tft_display.service"
    else
        echo "1. If you have a TFT display to configure:"
        echo "   ~/BirdNET-Pi/scripts/install_tft.sh"
        echo ""
        echo "2. To enable the service:"
        echo "   sudo systemctl enable --now tft_display.service"
    fi
    echo ""
    echo "Note: The service is installed but NOT enabled automatically."
    echo "      Configure your TFT hardware first if needed."
    echo ""
    log "Log file saved to: $LOG_FILE"
    exit 0
else
    log "ERROR: Installation failed"
    echo "ERROR: Installation failed. Please check the log at: $LOG_FILE"
    exit 1
fi
