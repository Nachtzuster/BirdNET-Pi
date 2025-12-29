#!/usr/bin/env bash
# TFT Display Detection Script
# Detects XPT2046 touch controller and SPI-based TFT displays
# Returns: 0 if TFT detected, 1 if not detected

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TFT_DETECTED=0
TOUCH_DETECTED=0
FRAMEBUFFER_DETECTED=0

echo "=== BirdNET-Pi TFT Display Detection ==="
echo ""

# Check for XPT2046 touchscreen controller
check_xpt2046() {
    echo -n "Checking for XPT2046 touch controller... "
    
    # Check in /proc/bus/input/devices
    if [ -f /proc/bus/input/devices ]; then
        if grep -qi "xpt2046\|ads7846" /proc/bus/input/devices; then
            echo -e "${GREEN}FOUND${NC}"
            TOUCH_DETECTED=1
            return 0
        fi
    fi
    
    # Check in dmesg
    if dmesg | grep -qi "xpt2046\|ads7846"; then
        echo -e "${GREEN}FOUND (in dmesg)${NC}"
        TOUCH_DETECTED=1
        return 0
    fi
    
    # Check for input event devices
    if ls /dev/input/event* &>/dev/null; then
        for event in /dev/input/event*; do
            if [ -c "$event" ]; then
                if timeout 0.5 evtest "$event" 2>/dev/null | head -5 | grep -qi "xpt2046\|ads7846\|touchscreen"; then
                    echo -e "${GREEN}FOUND${NC}"
                    TOUCH_DETECTED=1
                    return 0
                fi
            fi
        done
    fi
    
    echo -e "${YELLOW}NOT FOUND${NC}"
    return 1
}

# Check for SPI TFT display
check_spi_tft() {
    echo -n "Checking for SPI TFT display... "
    
    # Check for SPI devices
    if [ -d /sys/class/spi_master ]; then
        if ls /sys/class/spi_master/spi*/spi*.*/modalias 2>/dev/null | xargs cat 2>/dev/null | grep -qi "ili9341\|st7735\|st7789\|ili9488\|ili9486\|ssd1351"; then
            echo -e "${GREEN}FOUND${NC}"
            TFT_DETECTED=1
            return 0
        fi
    fi
    
    # Check in device tree
    if [ -d /proc/device-tree ]; then
        if find /proc/device-tree -name "compatible" -exec cat {} \; 2>/dev/null | grep -qi "ili9341\|st7735\|st7789\|ili9488\|ili9486\|ssd1351"; then
            echo -e "${GREEN}FOUND${NC}"
            TFT_DETECTED=1
            return 0
        fi
    fi
    
    # Check dmesg for common TFT drivers
    if dmesg | grep -qi "ili9341\|st7735\|st7789\|ili9488\|ili9486\|ssd1351\|fbtft"; then
        echo -e "${GREEN}FOUND (in dmesg)${NC}"
        TFT_DETECTED=1
        return 0
    fi
    
    echo -e "${YELLOW}NOT FOUND${NC}"
    return 1
}

# Check for framebuffer devices
check_framebuffer() {
    echo -n "Checking for framebuffer devices... "
    
    FB_COUNT=0
    for fb in /dev/fb*; do
        if [ -c "$fb" ]; then
            FB_COUNT=$((FB_COUNT + 1))
            if [ "$FB_COUNT" -eq 1 ]; then
                echo -ne "${GREEN}FOUND${NC}: "
            fi
            echo -n "$fb "
        fi
    done
    
    if [ "$FB_COUNT" -eq 0 ]; then
        echo -e "${RED}NOT FOUND${NC}"
        return 1
    else
        echo ""
        FRAMEBUFFER_DETECTED=1
        
        # Check if we have more than one framebuffer (indicates TFT likely configured)
        if [ "$FB_COUNT" -gt 1 ]; then
            echo "  → Multiple framebuffers detected (HDMI + TFT likely configured)"
        fi
        return 0
    fi
}

# Check SPI interface is enabled
check_spi_enabled() {
    echo -n "Checking if SPI is enabled... "
    
    if [ -d /sys/class/spi_master/spi0 ] || [ -d /sys/class/spi_master/spi1 ]; then
        echo -e "${GREEN}YES${NC}"
        return 0
    fi
    
    if lsmod | grep -q spi_bcm2835; then
        echo -e "${GREEN}YES${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}NO${NC}"
    echo "  → SPI needs to be enabled in /boot/firmware/config.txt"
    return 1
}

# Check for required tools
check_required_tools() {
    echo ""
    echo "Checking for required tools:"
    
    TOOLS_MISSING=0
    
    for tool in evtest; do
        echo -n "  - $tool: "
        if command -v $tool &>/dev/null; then
            echo -e "${GREEN}installed${NC}"
        else
            echo -e "${YELLOW}not installed${NC}"
            TOOLS_MISSING=1
        fi
    done
    
    if [ "$TOOLS_MISSING" -eq 1 ]; then
        echo ""
        echo "Note: Install missing tools with: sudo apt install evtest"
    fi
}

# Display summary
display_summary() {
    echo ""
    echo "=== Detection Summary ==="
    echo -n "XPT2046 Touch Controller: "
    [ "$TOUCH_DETECTED" -eq 1 ] && echo -e "${GREEN}Detected${NC}" || echo -e "${YELLOW}Not detected${NC}"
    
    echo -n "SPI TFT Display:          "
    [ "$TFT_DETECTED" -eq 1 ] && echo -e "${GREEN}Detected${NC}" || echo -e "${YELLOW}Not detected${NC}"
    
    echo -n "Framebuffer Devices:      "
    [ "$FRAMEBUFFER_DETECTED" -eq 1 ] && echo -e "${GREEN}Available${NC}" || echo -e "${RED}Not available${NC}"
    
    echo ""
    
    if [ "$TFT_DETECTED" -eq 1 ] || [ "$TOUCH_DETECTED" -eq 1 ]; then
        echo -e "${GREEN}✓ TFT display support appears to be configured${NC}"
        echo ""
        echo "You can proceed with enabling TFT display in BirdNET-Pi configuration."
        return 0
    else
        echo -e "${YELLOW}⚠ No TFT display detected${NC}"
        echo ""
        echo "If you have a TFT display connected, you may need to:"
        echo "  1. Enable SPI in /boot/firmware/config.txt"
        echo "  2. Add device tree overlay for your display"
        echo "  3. Install and configure display drivers"
        echo ""
        echo "Run ./install_tft.sh to install TFT support."
        return 1
    fi
}

# Main execution
main() {
    check_spi_enabled
    echo ""
    check_xpt2046
    check_spi_tft
    check_framebuffer
    check_required_tools
    display_summary
    
    # Return appropriate exit code
    if [ "$TFT_DETECTED" -eq 1 ] || [ "$TOUCH_DETECTED" -eq 1 ] || [ "$FRAMEBUFFER_DETECTED" -gt 1 ]; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
