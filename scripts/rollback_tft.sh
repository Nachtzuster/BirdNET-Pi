#!/usr/bin/env bash
# TFT Display Rollback Script for BirdNET-Pi
# Restores original configuration before TFT installation

set -e

# Configuration
BACKUP_DIR="${HOME}/BirdNET-Pi/tft_backups"
CONFIG_FILE="/boot/firmware/config.txt"
BIRDNET_CONF="/etc/birdnet/birdnet.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== BirdNET-Pi TFT Display Rollback ===${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run as a non-root user with sudo privileges.${NC}"
    exit 1
fi

# Check if backup directory exists
if [ ! -d "${BACKUP_DIR}" ]; then
    echo -e "${RED}Error: Backup directory not found at ${BACKUP_DIR}${NC}"
    echo "No TFT installation detected or backups were not created."
    exit 1
fi

# List available backups
list_backups() {
    echo "Available backups:"
    echo ""
    
    if [ -f "${BACKUP_DIR}/last_backup.txt" ]; then
        LAST_BACKUP=$(cat "${BACKUP_DIR}/last_backup.txt")
        echo -e "${GREEN}Most recent backup: ${LAST_BACKUP}${NC}"
    fi
    
    echo ""
    echo "Backup files:"
    ls -lh "${BACKUP_DIR}"/*.* 2>/dev/null || echo "No backup files found"
    echo ""
}

# Stop TFT display service
stop_tft_service() {
    echo -n "Stopping TFT display service... "
    
    if systemctl is-active --quiet tft_display.service; then
        sudo systemctl stop tft_display.service
        echo -e "${GREEN}Stopped${NC}"
    else
        echo -e "${YELLOW}Not running${NC}"
    fi
    
    echo -n "Disabling TFT display service... "
    if systemctl is-enabled --quiet tft_display.service 2>/dev/null; then
        sudo systemctl disable tft_display.service
        echo -e "${GREEN}Disabled${NC}"
    else
        echo -e "${YELLOW}Not enabled${NC}"
    fi
}

# Restore configuration files
restore_configs() {
    if [ ! -f "${BACKUP_DIR}/last_backup.txt" ]; then
        echo -e "${YELLOW}Warning: No backup timestamp found${NC}"
        echo "Looking for most recent backup files..."
        
        # Find most recent backup by timestamp
        LATEST_CONFIG=$(ls -t "${BACKUP_DIR}"/config.txt.* 2>/dev/null | head -1)
        LATEST_BIRDNET=$(ls -t "${BACKUP_DIR}"/birdnet.conf.* 2>/dev/null | head -1)
    else
        TIMESTAMP=$(cat "${BACKUP_DIR}/last_backup.txt")
        LATEST_CONFIG="${BACKUP_DIR}/config.txt.${TIMESTAMP}"
        LATEST_BIRDNET="${BACKUP_DIR}/birdnet.conf.${TIMESTAMP}"
    fi
    
    echo ""
    echo "Restoring configuration files..."
    
    # Restore boot config
    if [ -f "${LATEST_CONFIG}" ]; then
        echo -n "  - Restoring ${CONFIG_FILE}... "
        sudo cp "${LATEST_CONFIG}" "${CONFIG_FILE}"
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}  - Warning: No backup found for ${CONFIG_FILE}${NC}"
        echo "    Manual restoration may be required."
    fi
    
    # Restore BirdNET config
    if [ -f "${LATEST_BIRDNET}" ]; then
        echo -n "  - Restoring ${BIRDNET_CONF}... "
        sudo cp "${LATEST_BIRDNET}" "${BIRDNET_CONF}"
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}  - Warning: No backup found for ${BIRDNET_CONF}${NC}"
        echo "    TFT configuration may still be present."
        
        # Try to remove TFT configuration manually
        if [ -f "${BIRDNET_CONF}" ]; then
            echo -n "    Removing TFT configuration from ${BIRDNET_CONF}... "
            sudo sed -i '/^# TFT Display Configuration/,/^TFT_TYPE=/d' "${BIRDNET_CONF}"
            sudo sed -i '/^TFT_/d' "${BIRDNET_CONF}"
            echo -e "${GREEN}OK${NC}"
        fi
    fi
}

# Remove TFT service file
remove_tft_service() {
    echo ""
    echo -n "Removing TFT display service file... "
    
    if [ -f "${HOME}/BirdNET-Pi/templates/tft_display.service" ]; then
        rm -f "${HOME}/BirdNET-Pi/templates/tft_display.service"
    fi
    
    if [ -f "/usr/lib/systemd/system/tft_display.service" ]; then
        sudo rm -f "/usr/lib/systemd/system/tft_display.service"
    fi
    
    # Remove the installed script from /usr/local/bin
    if [ -f "/usr/local/bin/tft_display.py" ]; then
        sudo rm -f "/usr/local/bin/tft_display.py"
    fi
    
    sudo systemctl daemon-reload
    echo -e "${GREEN}OK${NC}"
}

# Display verification instructions
display_verification() {
    echo ""
    echo -e "${GREEN}=== Rollback Complete ===${NC}"
    echo ""
    echo "Configuration files have been restored to their state before TFT installation."
    echo ""
    echo "Next steps:"
    echo "  1. Verify the restored configuration: sudo cat ${CONFIG_FILE}"
    echo "  2. Reboot your Raspberry Pi: sudo reboot"
    echo "  3. After reboot, verify TFT is not detected: ./detect_tft.sh"
    echo ""
    echo "The TFT display should no longer be active after reboot."
    echo "HDMI output should work normally."
    echo ""
    echo "Backup files are still available in: ${BACKUP_DIR}"
    echo "You can delete them manually if no longer needed."
    echo ""
    echo -e "${YELLOW}⚠ Reboot is required for changes to take effect${NC}"
    echo ""
}

# Optional: Remove Python packages
remove_python_packages() {
    echo ""
    read -p "Remove TFT Python packages (luma.lcd, luma.core)? (y/n): " remove_py
    
    if [ "$remove_py" = "y" ] || [ "$remove_py" = "Y" ]; then
        echo "Removing Python packages..."
        
        if [ -d "${HOME}/BirdNET-Pi/birdnet" ]; then
            source "${HOME}/BirdNET-Pi/birdnet/bin/activate"
            pip3 uninstall -y luma.lcd luma.core || true
            echo -e "${GREEN}Python packages removed${NC}"
        fi
    fi
}

# Optional: Remove backup files
remove_backups() {
    echo ""
    read -p "Remove all TFT backup files? (y/n): " remove_bak
    
    if [ "$remove_bak" = "y" ] || [ "$remove_bak" = "Y" ]; then
        echo -n "Removing backup directory... "
        rm -rf "${BACKUP_DIR}"
        echo -e "${GREEN}OK${NC}"
        echo "All TFT backup files have been removed."
    fi
}

# Main rollback flow
main() {
    list_backups
    
    echo -e "${YELLOW}This script will restore your configuration to the state before TFT installation.${NC}"
    echo "This will:"
    echo "  - Stop and disable the TFT display service"
    echo "  - Restore original configuration files"
    echo "  - Remove TFT-specific configuration"
    echo ""
    read -p "Continue with rollback? (y/n): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Rollback cancelled."
        exit 0
    fi
    
    stop_tft_service
    restore_configs
    remove_tft_service
    remove_python_packages
    display_verification
    remove_backups
    
    echo ""
    read -p "Reboot now? (y/n): " reboot_choice
    if [ "$reboot_choice" = "y" ] || [ "$reboot_choice" = "Y" ]; then
        echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
        sleep 5
        sudo reboot
    fi
}

main "$@"
