#!/usr/bin/env bash
# Automatic TFT Display Detection and Configuration Script
# This script automatically detects and configures SPI TFT displays for BirdNET-Pi
# It runs at boot to ensure TFT displays are always properly configured

set -e

# Configuration
BIRDNET_CONF="/etc/birdnet/birdnet.conf"
CONFIG_FILE="/boot/firmware/config.txt"
BACKUP_DIR="${HOME}/BirdNET-Pi/tft_backups"
LOG_FILE="/tmp/auto_configure_tft.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Automatic TFT Display Configuration ==="

# Detect TFT display type from hardware
detect_tft_type() {
    local tft_type=""
    
    # Check device tree for display type - run find once and check all patterns
    if [ -d /proc/device-tree ]; then
        local compatible_output=$(find /proc/device-tree -name "compatible" -exec cat {} \; 2>/dev/null)
        
        if echo "$compatible_output" | grep -qi "ili9341"; then
            tft_type="ili9341"
        elif echo "$compatible_output" | grep -qi "st7735"; then
            tft_type="st7735r"
        elif echo "$compatible_output" | grep -qi "st7789"; then
            tft_type="st7789"
        elif echo "$compatible_output" | grep -qi "ili9488"; then
            tft_type="ili9488"
        elif echo "$compatible_output" | grep -qi "ili9486"; then
            tft_type="ili9486"
        fi
    fi
    
    # Check dmesg for display initialization messages
    if [ -z "$tft_type" ]; then
        if dmesg | grep -qi "ili9341"; then
            tft_type="ili9341"
        elif dmesg | grep -qi "st7735"; then
            tft_type="st7735r"
        elif dmesg | grep -qi "st7789"; then
            tft_type="st7789"
        elif dmesg | grep -qi "ili9488"; then
            tft_type="ili9488"
        elif dmesg | grep -qi "ili9486"; then
            tft_type="ili9486"
        fi
    fi
    
    # Check config.txt for configured overlay
    if [ -z "$tft_type" ] && [ -f "$CONFIG_FILE" ]; then
        if grep -qi "piscreen," "$CONFIG_FILE" || grep -qi "ili9341" "$CONFIG_FILE"; then
            tft_type="ili9341"
        elif grep -qi "piscreen2r" "$CONFIG_FILE" || grep -qi "st7735" "$CONFIG_FILE"; then
            tft_type="st7735r"
        elif grep -qi "st7789" "$CONFIG_FILE"; then
            tft_type="st7789"
        elif grep -qi "waveshare35a" "$CONFIG_FILE" || grep -qi "ili9488" "$CONFIG_FILE"; then
            tft_type="ili9488"
        elif grep -qi "ili9486" "$CONFIG_FILE"; then
            tft_type="ili9486"
        fi
    fi
    
    echo "$tft_type"
}

# Detect framebuffer resolution
detect_resolution() {
    local fb_device="${1:-/dev/fb1}"
    
    if [ ! -c "$fb_device" ]; then
        return 1
    fi
    
    # Try fbset first
    if command -v fbset &>/dev/null; then
        local resolution=$(fbset -fb "$fb_device" 2>/dev/null | grep "geometry" | awk '{print $2"x"$3}')
        if [ -n "$resolution" ]; then
            echo "$resolution"
            return 0
        fi
    fi
    
    # Fallback to sysfs
    local fb_name=$(basename "$fb_device")
    if [ -f "/sys/class/graphics/$fb_name/virtual_size" ]; then
        local resolution=$(cat "/sys/class/graphics/$fb_name/virtual_size" | tr ',' 'x')
        if [ -n "$resolution" ]; then
            echo "$resolution"
            return 0
        fi
    fi
    
    return 1
}

# Check if TFT hardware is present
check_tft_hardware() {
    log "Checking for TFT hardware..."
    
    # Check for framebuffer devices (fb1 or higher indicates TFT)
    if [ -c /dev/fb1 ]; then
        log "✓ Framebuffer device /dev/fb1 found"
        return 0
    fi
    
    # Check for SPI devices
    if [ -d /sys/class/spi_master ]; then
        if ls /sys/class/spi_master/spi*/spi*.*/modalias 2>/dev/null | xargs cat 2>/dev/null | grep -qi "ili9341\|st7735\|st7789\|ili9488\|ili9486"; then
            log "✓ SPI TFT device found"
            return 0
        fi
    fi
    
    # Check config.txt for TFT configuration
    if [ -f "$CONFIG_FILE" ]; then
        if grep -qE "dtoverlay=(tft|ili9341|st7735|st7789|piscreen|waveshare)" "$CONFIG_FILE"; then
            log "✓ TFT overlay configured in $CONFIG_FILE"
            return 0
        fi
    fi
    
    log "No TFT hardware detected"
    return 1
}

# Update or create birdnet.conf with TFT settings
update_birdnet_conf() {
    local tft_type="$1"
    local resolution="$2"
    local rotation="$3"
    
    log "Updating BirdNET configuration..."
    
    if [ ! -f "$BIRDNET_CONF" ]; then
        log "Creating $BIRDNET_CONF"
        sudo mkdir -p "$(dirname "$BIRDNET_CONF")"
        sudo touch "$BIRDNET_CONF"
    fi
    
    # Backup existing configuration
    if [ -f "$BIRDNET_CONF" ]; then
        mkdir -p "$BACKUP_DIR"
        local timestamp=$(date +%Y%m%d_%H%M%S)
        sudo cp "$BIRDNET_CONF" "${BACKUP_DIR}/birdnet.conf.${timestamp}.auto"
    fi
    
    # Remove old TFT configuration lines
    sudo sed -i '/^TFT_/d' "$BIRDNET_CONF"
    
    # Add new TFT configuration
    cat << EOF | sudo tee -a "$BIRDNET_CONF" > /dev/null

# TFT Display Configuration (Auto-configured)
TFT_ENABLED=1
TFT_TYPE=${tft_type}
TFT_DEVICE=/dev/fb1
TFT_ROTATION=${rotation}
TFT_FONT_SIZE=12
TFT_SCROLL_SPEED=2
TFT_MAX_DETECTIONS=20
TFT_UPDATE_INTERVAL=5
TFT_SCREENSAVER_TIMEOUT=300
TFT_SCREENSAVER_BRIGHTNESS=0
EOF
    
    log "✓ Configuration updated with TFT settings"
}

# Ensure SPI and TFT are enabled in config.txt
ensure_boot_config() {
    local needs_reboot=false
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log "Boot config file not found at $CONFIG_FILE"
        return 1
    fi
    
    log "Checking boot configuration..."
    
    # Check if SPI is enabled
    if ! grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
        log "Enabling SPI in boot config"
        echo "dtparam=spi=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
        needs_reboot=true
    fi
    
    # Check if any TFT overlay is configured
    if ! grep -qE "dtoverlay=(tft|ili9341|st7735|st7789|piscreen|waveshare)" "$CONFIG_FILE"; then
        log "No TFT overlay detected in boot config"
        log "TFT hardware configuration may be incomplete"
    fi
    
    if [ "$needs_reboot" = true ]; then
        log "⚠ Boot configuration changed - reboot required"
        return 2
    fi
    
    return 0
}

# Main auto-configuration logic
main() {
    log "Starting automatic TFT configuration check..."
    
    # Check if TFT hardware is present
    if ! check_tft_hardware; then
        log "No TFT hardware detected - skipping configuration"
        
        # If no hardware but TFT is enabled in config, disable it
        if [ -f "$BIRDNET_CONF" ] && grep -q "^TFT_ENABLED=1" "$BIRDNET_CONF"; then
            log "Disabling TFT in configuration (no hardware detected)"
            sudo sed -i 's/^TFT_ENABLED=1/TFT_ENABLED=0/' "$BIRDNET_CONF"
        fi
        
        exit 0
    fi
    
    # Detect TFT type
    tft_type=$(detect_tft_type)
    if [ -z "$tft_type" ]; then
        log "Could not determine TFT type, using default (ili9341)"
        tft_type="ili9341"
    else
        log "Detected TFT type: $tft_type"
    fi
    
    # Detect resolution
    resolution=$(detect_resolution "/dev/fb1")
    if [ -n "$resolution" ]; then
        log "Detected resolution: $resolution"
    else
        log "Could not detect resolution, will use device defaults"
        resolution="240x320"  # Default for most TFT displays
    fi
    
    # Set portrait mode rotation (90 degrees)
    rotation=90
    log "Using portrait mode rotation: ${rotation}°"
    
    # Update birdnet.conf with detected settings
    update_birdnet_conf "$tft_type" "$resolution" "$rotation"
    
    # Ensure boot configuration is correct
    ensure_boot_config
    boot_config_result=$?
    
    if [ $boot_config_result -eq 2 ]; then
        log "Boot configuration was modified - system reboot recommended"
        log "TFT display will be fully active after reboot"
    fi
    
    log "=== Automatic TFT configuration complete ==="
    
    # Enable and start the TFT display service if not already enabled
    if systemctl is-enabled tft_display.service &>/dev/null; then
        log "TFT display service is already enabled"
    else
        log "Enabling TFT display service..."
        sudo systemctl enable tft_display.service
    fi
    
    # Restart the service to apply new configuration
    if systemctl is-active tft_display.service &>/dev/null; then
        log "Restarting TFT display service..."
        sudo systemctl restart tft_display.service || log "Service restart will complete after dependencies are ready"
    fi
    
    exit 0
}

main "$@"
