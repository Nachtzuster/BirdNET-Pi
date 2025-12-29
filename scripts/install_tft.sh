#!/usr/bin/env bash
# TFT Display Installation Script for BirdNET-Pi
# Installs support for XPT2046 touch controller and SPI TFT displays
# Supports Raspberry Pi 4B with Trixie distribution

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

# Display options
TFT_TYPE=""
TFT_ROTATION=90  # Portrait mode by default

echo -e "${BLUE}=== BirdNET-Pi TFT Display Installation ===${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run as a non-root user with sudo privileges.${NC}"
    exit 1
fi

# Create backup directory
create_backup_dir() {
    echo -n "Creating backup directory... "
    mkdir -p "${BACKUP_DIR}"
    echo -e "${GREEN}OK${NC}"
}

# Backup configuration files
backup_configs() {
    echo "Backing up configuration files..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    
    if [ -f "${CONFIG_FILE}" ]; then
        echo -n "  - Backing up ${CONFIG_FILE}... "
        sudo cp "${CONFIG_FILE}" "${BACKUP_DIR}/config.txt.${TIMESTAMP}"
        echo -e "${GREEN}OK${NC}"
    fi
    
    if [ -f "${BIRDNET_CONF}" ]; then
        echo -n "  - Backing up ${BIRDNET_CONF}... "
        sudo cp "${BIRDNET_CONF}" "${BACKUP_DIR}/birdnet.conf.${TIMESTAMP}"
        echo -e "${GREEN}OK${NC}"
    fi
    
    # Save backup timestamp for rollback
    echo "${TIMESTAMP}" > "${BACKUP_DIR}/last_backup.txt"
    
    echo -e "${GREEN}Backups created in ${BACKUP_DIR}${NC}"
}

# Install required packages
install_packages() {
    echo ""
    echo "Installing required packages..."
    
    # Update package list
    echo "Updating package list..."
    sudo apt-get update -qq
    
    # Install base dependencies
    echo "Installing base dependencies..."
    sudo apt-get install -y \
        build-essential \
        cmake \
        git \
        evtest \
        python3-dev \
        python3-pip \
        libfreetype6-dev \
        libjpeg-dev \
        libopenjp2-7 \
        libtiff5
    
    echo -e "${GREEN}Base packages installed${NC}"
}

# Install Python packages for TFT display
install_python_packages() {
    echo ""
    echo "Installing Python packages for TFT display..."
    
    # Activate virtual environment
    if [ -d "${HOME}/BirdNET-Pi/birdnet" ]; then
        source "${HOME}/BirdNET-Pi/birdnet/bin/activate"
        
        # Install required Python packages
        pip3 install --upgrade pip setuptools wheel
        pip3 install luma.lcd luma.core
        
        echo -e "${GREEN}Python packages installed${NC}"
    else
        echo -e "${YELLOW}Warning: BirdNET-Pi virtual environment not found${NC}"
        echo "Run this script after BirdNET-Pi installation is complete."
    fi
}

# Select TFT display type
select_display_type() {
    echo ""
    echo "Select your TFT display type:"
    echo "  1) ILI9341 (240x320) - Common cheap displays"
    echo "  2) ST7735 (128x160) - Small displays"
    echo "  3) ST7789 (240x240) - Square displays"
    echo "  4) ILI9488 (320x480) - Larger displays"
    echo "  5) Custom/Other"
    echo "  6) Skip display configuration (manual setup)"
    echo ""
    read -p "Enter your choice [1-6]: " choice
    
    case $choice in
        1) TFT_TYPE="ili9341" ;;
        2) TFT_TYPE="st7735r" ;;
        3) TFT_TYPE="st7789" ;;
        4) TFT_TYPE="ili9488" ;;
        5) 
            read -p "Enter your display type: " TFT_TYPE
            ;;
        6)
            echo "Skipping display configuration."
            TFT_TYPE=""
            return
            ;;
        *)
            echo "Invalid choice. Defaulting to ILI9341."
            TFT_TYPE="ili9341"
            ;;
    esac
    
    echo -e "${GREEN}Selected display type: ${TFT_TYPE}${NC}"
}

# Configure boot config for TFT
configure_boot_config() {
    if [ -z "$TFT_TYPE" ]; then
        echo "Skipping boot configuration (no display type selected)."
        return
    fi
    
    echo ""
    echo "Configuring ${CONFIG_FILE} for TFT display..."
    
    # Check if file exists
    if [ ! -f "${CONFIG_FILE}" ]; then
        echo -e "${YELLOW}Warning: ${CONFIG_FILE} not found${NC}"
        echo "Creating basic configuration..."
        sudo touch "${CONFIG_FILE}"
    fi
    
    # Enable SPI
    echo -n "  - Enabling SPI... "
    if ! grep -q "^dtparam=spi=on" "${CONFIG_FILE}"; then
        echo "dtparam=spi=on" | sudo tee -a "${CONFIG_FILE}" > /dev/null
    fi
    echo -e "${GREEN}OK${NC}"
    
    # Add TFT overlay based on display type
    echo -n "  - Adding display overlay... "
    
    # Remove old TFT configurations if present
    sudo sed -i '/dtoverlay=.*tft/d' "${CONFIG_FILE}"
    sudo sed -i '/dtoverlay=.*ili9341/d' "${CONFIG_FILE}"
    sudo sed -i '/dtoverlay=.*st7735/d' "${CONFIG_FILE}"
    sudo sed -i '/dtoverlay=.*st7789/d' "${CONFIG_FILE}"
    sudo sed -i '/dtoverlay=.*ili9488/d' "${CONFIG_FILE}"
    
    # Add appropriate overlay
    case "$TFT_TYPE" in
        ili9341)
            echo "dtoverlay=piscreen,speed=16000000,rotate=${TFT_ROTATION}" | sudo tee -a "${CONFIG_FILE}" > /dev/null
            ;;
        st7735r)
            echo "dtoverlay=piscreen2r,speed=16000000,rotate=${TFT_ROTATION}" | sudo tee -a "${CONFIG_FILE}" > /dev/null
            ;;
        st7789)
            echo "dtoverlay=vc4-kms-v3d" | sudo tee -a "${CONFIG_FILE}" > /dev/null
            echo "dtoverlay=vc4-kms-dpi-generic" | sudo tee -a "${CONFIG_FILE}" > /dev/null
            ;;
        ili9488)
            echo "dtoverlay=waveshare35a,speed=16000000,rotate=${TFT_ROTATION}" | sudo tee -a "${CONFIG_FILE}" > /dev/null
            ;;
    esac
    
    echo -e "${GREEN}OK${NC}"
    
    # Add touchscreen overlay for XPT2046
    echo -n "  - Adding touchscreen overlay... "
    if ! grep -q "dtoverlay=ads7846" "${CONFIG_FILE}"; then
        echo "dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900" | sudo tee -a "${CONFIG_FILE}" > /dev/null
    fi
    echo -e "${GREEN}OK${NC}"
    
    echo -e "${GREEN}Boot configuration updated${NC}"
}

# Add TFT configuration to birdnet.conf
configure_birdnet() {
    echo ""
    echo "Updating BirdNET-Pi configuration..."
    
    if [ ! -f "${BIRDNET_CONF}" ]; then
        echo -e "${YELLOW}Warning: ${BIRDNET_CONF} not found${NC}"
        echo "TFT configuration will need to be added manually."
        return
    fi
    
    # Remove old TFT configuration if present
    sudo sed -i '/^TFT_/d' "${BIRDNET_CONF}"
    
    # Add TFT configuration section
    cat << EOF | sudo tee -a "${BIRDNET_CONF}" > /dev/null

# TFT Display Configuration
TFT_ENABLED=0
TFT_DEVICE=/dev/fb1
TFT_ROTATION=${TFT_ROTATION}
TFT_FONT_SIZE=12
TFT_SCROLL_SPEED=2
TFT_MAX_DETECTIONS=20
TFT_UPDATE_INTERVAL=5
TFT_TYPE=${TFT_TYPE}
EOF
    
    echo -e "${GREEN}BirdNET-Pi configuration updated${NC}"
    echo ""
    echo "Note: TFT display is disabled by default (TFT_ENABLED=0)"
    echo "Enable it by setting TFT_ENABLED=1 in ${BIRDNET_CONF}"
}

# Display completion message
display_completion() {
    echo ""
    echo -e "${GREEN}=== TFT Display Installation Complete ===${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Reboot your Raspberry Pi: sudo reboot"
    echo "  2. After reboot, verify detection: ./detect_tft.sh"
    echo "  3. Enable TFT display by editing ${BIRDNET_CONF}"
    echo "     Set: TFT_ENABLED=1"
    echo "  4. Restart BirdNET-Pi services or reboot again"
    echo ""
    echo "Configuration backups saved in: ${BACKUP_DIR}"
    echo "To rollback, run: ./rollback_tft.sh"
    echo ""
    echo -e "${YELLOW}⚠ Reboot is required for changes to take effect${NC}"
    echo ""
    read -p "Reboot now? (y/n): " reboot_choice
    if [ "$reboot_choice" = "y" ] || [ "$reboot_choice" = "Y" ]; then
        echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
        sleep 5
        sudo reboot
    fi
}

# Main installation flow
main() {
    echo "This script will install TFT display support for BirdNET-Pi."
    echo "It will modify system configuration files."
    echo ""
    read -p "Continue? (y/n): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    create_backup_dir
    backup_configs
    install_packages
    install_python_packages
    select_display_type
    configure_boot_config
    configure_birdnet
    display_completion
}

main "$@"
