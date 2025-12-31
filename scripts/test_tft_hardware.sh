#!/usr/bin/env bash
# TFT Display Hardware Test Script for Debian Trixie
# This script tests if the SPI TFT display is properly configured and accessible
# Run this to verify your TFT hardware works outside of BirdNET-Pi

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== TFT Display Hardware Test for Debian Trixie ===${NC}"
echo ""
echo "This script will test your SPI TFT display configuration"
echo "and verify it works independently of BirdNET-Pi."
echo ""

# Function to print test results
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
    fi
}

# Test 1: Check if running on Raspberry Pi
echo -e "${BLUE}Test 1: System Information${NC}"
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo "  Model: $MODEL"
    test_result 0 "Raspberry Pi detected"
else
    echo "  Not running on Raspberry Pi"
    test_result 1 "Raspberry Pi detection"
fi

# Check Debian version
if [ -f /etc/debian_version ]; then
    DEBIAN_VERSION=$(cat /etc/debian_version)
    echo "  Debian version: $DEBIAN_VERSION"
    if [[ "$DEBIAN_VERSION" =~ ^13 ]] || [[ "$DEBIAN_VERSION" == "trixie"* ]]; then
        test_result 0 "Debian Trixie (13) detected"
    else
        echo -e "  ${YELLOW}Warning: Not running Debian Trixie${NC}"
    fi
fi

# Check kernel version
KERNEL=$(uname -r)
echo "  Kernel: $KERNEL"
echo ""

# Test 2: Check for SPI support
echo -e "${BLUE}Test 2: SPI Kernel Module${NC}"
if lsmod | grep -q spi_bcm2835; then
    test_result 0 "SPI kernel module (spi_bcm2835) loaded"
else
    test_result 1 "SPI kernel module not loaded"
    echo "  ${YELLOW}Try: sudo modprobe spi_bcm2835${NC}"
fi
echo ""

# Test 3: Check /dev/spi devices
echo -e "${BLUE}Test 3: SPI Device Files${NC}"
if ls /dev/spidev* &>/dev/null; then
    echo "  Found SPI devices:"
    ls -l /dev/spidev*
    test_result 0 "SPI device files exist"
else
    test_result 1 "No SPI device files found"
    echo "  ${YELLOW}Enable SPI in /boot/firmware/config.txt${NC}"
fi
echo ""

# Test 4: Check framebuffer devices
echo -e "${BLUE}Test 4: Framebuffer Devices${NC}"
if ls /dev/fb* &>/dev/null; then
    echo "  Found framebuffer devices:"
    for fb in /dev/fb*; do
        echo "    $fb"
        if [ -f "/sys/class/graphics/$(basename $fb)/name" ]; then
            NAME=$(cat "/sys/class/graphics/$(basename $fb)/name")
            echo "      Name: $NAME"
        fi
        if [ -f "/sys/class/graphics/$(basename $fb)/virtual_size" ]; then
            SIZE=$(cat "/sys/class/graphics/$(basename $fb)/virtual_size")
            echo "      Size: $SIZE"
        fi
    done
    test_result 0 "Framebuffer devices found"
    
    # Check specifically for fb1 (typically TFT)
    if [ -e /dev/fb1 ]; then
        test_result 0 "Secondary framebuffer (/dev/fb1) exists"
    else
        test_result 1 "Secondary framebuffer (/dev/fb1) not found"
    fi
else
    test_result 1 "No framebuffer devices found"
fi
echo ""

# Test 5: Check boot config
echo -e "${BLUE}Test 5: Boot Configuration${NC}"
CONFIG_FILE="/boot/firmware/config.txt"
if [ -f "$CONFIG_FILE" ]; then
    echo "  Checking $CONFIG_FILE..."
    
    if grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
        test_result 0 "SPI enabled in config.txt"
    else
        test_result 1 "SPI not enabled in config.txt"
    fi
    
    if grep -qE "^dtoverlay=.*tft|^dtoverlay=.*ili9341|^dtoverlay=.*ili9486|^dtoverlay=.*st7735|^dtoverlay=.*st7789" "$CONFIG_FILE"; then
        echo "  Found TFT overlays:"
        grep -E "^dtoverlay=.*tft|^dtoverlay=.*ili9341|^dtoverlay=.*ili9486|^dtoverlay=.*st7735|^dtoverlay=.*st7789" "$CONFIG_FILE" | sed 's/^/    /'
        test_result 0 "TFT device tree overlay configured"
    else
        test_result 1 "No TFT device tree overlay found"
    fi
else
    test_result 1 "Config file $CONFIG_FILE not found"
fi
echo ""

# Test 6: Check for required system packages (Debian Trixie)
echo -e "${BLUE}Test 6: System Packages for Debian Trixie${NC}"
REQUIRED_PACKAGES=(
    "python3"
    "python3-pip"
    "python3-dev"
    "libfreetype6"
    "libjpeg62-turbo"
    "libopenjp2-7"
    "libtiff6"
)

ALL_INSTALLED=true
for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if dpkg -l | grep -q "^ii  $pkg"; then
        test_result 0 "Package $pkg installed"
    else
        test_result 1 "Package $pkg NOT installed"
        ALL_INSTALLED=false
    fi
done

if [ "$ALL_INSTALLED" = false ]; then
    echo ""
    echo -e "${YELLOW}To install missing packages:${NC}"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install python3 python3-pip python3-dev libfreetype6 libjpeg62-turbo libopenjp2-7 libtiff6"
fi
echo ""

# Test 7: Check Python packages
echo -e "${BLUE}Test 7: Python Packages${NC}"
echo "  Testing with system Python ($(which python3))..."

# Test luma.lcd
if python3 -c "import luma.lcd" 2>/dev/null; then
    test_result 0 "luma.lcd importable"
    LUMA_VERSION=$(python3 -c "import luma.lcd; print(luma.lcd.__version__)" 2>/dev/null || echo "unknown")
    echo "    Version: $LUMA_VERSION"
else
    test_result 1 "luma.lcd not found"
    echo "    ${YELLOW}Install with: pip3 install luma.lcd${NC}"
fi

# Test luma.core
if python3 -c "import luma.core" 2>/dev/null; then
    test_result 0 "luma.core importable"
else
    test_result 1 "luma.core not found"
    echo "    ${YELLOW}Install with: pip3 install luma.core${NC}"
fi

# Test PIL/Pillow
if python3 -c "import PIL" 2>/dev/null; then
    test_result 0 "PIL/Pillow importable"
    PIL_VERSION=$(python3 -c "import PIL; print(PIL.__version__)" 2>/dev/null || echo "unknown")
    echo "    Version: $PIL_VERSION"
else
    test_result 1 "PIL/Pillow not found"
    echo "    ${YELLOW}Install with: pip3 install Pillow${NC}"
fi

# Check BirdNET-Pi virtual environment if it exists
if [ -d "$HOME/BirdNET-Pi/birdnet" ]; then
    echo ""
    echo "  Testing with BirdNET-Pi virtual environment..."
    VENV_PYTHON="$HOME/BirdNET-Pi/birdnet/bin/python3"
    
    if [ -f "$VENV_PYTHON" ]; then
        if $VENV_PYTHON -c "import luma.lcd" 2>/dev/null; then
            test_result 0 "luma.lcd available in venv"
        else
            test_result 1 "luma.lcd NOT in venv"
            echo "    ${YELLOW}Install with: $HOME/BirdNET-Pi/birdnet/bin/pip install luma.lcd${NC}"
        fi
        
        if $VENV_PYTHON -c "import PIL" 2>/dev/null; then
            test_result 0 "Pillow available in venv"
        else
            test_result 1 "Pillow NOT in venv"
            echo "    ${YELLOW}Install with: $HOME/BirdNET-Pi/birdnet/bin/pip install Pillow${NC}"
        fi
    fi
fi
echo ""

# Test 8: Test SPI communication (requires luma)
echo -e "${BLUE}Test 8: SPI Communication Test${NC}"
if python3 -c "import luma.core" 2>/dev/null; then
    echo "  Creating minimal SPI test..."
    
    # Create a temporary test script
    TEST_SCRIPT="/tmp/spi_test_$$.py"
    cat > "$TEST_SCRIPT" << 'EOFPYTHON'
#!/usr/bin/env python3
import sys
try:
    from luma.core.interface.serial import spi
    
    # Try to create SPI interface (won't initialize without hardware)
    serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
    print("✓ SPI interface object created successfully")
    print("  Note: Actual communication requires connected hardware")
    sys.exit(0)
except PermissionError as e:
    print(f"✗ Permission error: {e}")
    print("  Try running with sudo or add user to 'spi' and 'gpio' groups")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
EOFPYTHON
    
    if python3 "$TEST_SCRIPT"; then
        test_result 0 "SPI interface initialization"
    else
        test_result 1 "SPI interface initialization failed"
    fi
    rm -f "$TEST_SCRIPT"
else
    echo "  ${YELLOW}Skipping (luma.core not installed)${NC}"
fi
echo ""

# Test 9: GPIO access
echo -e "${BLUE}Test 9: GPIO Access${NC}"
if [ -d /sys/class/gpio ]; then
    test_result 0 "GPIO sysfs interface exists"
    
    # Check user groups
    CURRENT_USER=$(whoami)
    if groups | grep -qE 'gpio|spi'; then
        test_result 0 "User in gpio/spi group"
    else
        test_result 1 "User NOT in gpio/spi group"
        echo "    ${YELLOW}Add with: sudo usermod -a -G gpio,spi $CURRENT_USER${NC}"
        echo "    ${YELLOW}Then log out and back in${NC}"
    fi
else
    test_result 1 "GPIO sysfs interface not found"
fi
echo ""

# Test 10: Device tree overlays
echo -e "${BLUE}Test 10: Loaded Device Tree Overlays${NC}"
if [ -d /proc/device-tree/soc ]; then
    if ls /proc/device-tree/soc/*spi* &>/dev/null; then
        echo "  Found SPI device tree entries:"
        ls /proc/device-tree/soc/*spi* | head -5 | sed 's/^/    /'
        test_result 0 "SPI device tree entries present"
    else
        test_result 1 "No SPI device tree entries found"
    fi
else
    echo "  ${YELLOW}Device tree information not accessible${NC}"
fi
echo ""

# Summary and recommendations
echo -e "${BLUE}=== Summary and Next Steps ===${NC}"
echo ""
echo "If all tests passed, your TFT display should work with BirdNET-Pi."
echo ""
echo -e "${YELLOW}Common issues and fixes:${NC}"
echo ""
echo "1. ${BOLD}SPI not enabled:${NC}"
echo "   Edit /boot/firmware/config.txt and add: dtparam=spi=on"
echo "   Then reboot"
echo ""
echo "2. ${BOLD}No TFT overlay configured:${NC}"
echo "   Add to /boot/firmware/config.txt:"
echo "   - For ILI9341: dtoverlay=piscreen,speed=16000000,rotate=90"
echo "   - For ILI9486: dtoverlay=waveshare35a,speed=16000000,rotate=90"
echo "   - For ST7735: dtoverlay=piscreen2r,speed=16000000,rotate=90"
echo "   Then reboot"
echo ""
echo "3. ${BOLD}Python packages missing in BirdNET-Pi venv:${NC}"
echo "   source ~/BirdNET-Pi/birdnet/bin/activate"
echo "   pip install luma.lcd luma.core Pillow"
echo "   deactivate"
echo ""
echo "4. ${BOLD}Permission issues:${NC}"
echo "   sudo usermod -a -G gpio,spi \$USER"
echo "   Log out and back in"
echo ""
echo "5. ${BOLD}Check kernel logs:${NC}"
echo "   dmesg | grep -i spi"
echo "   dmesg | grep -i fb"
echo ""
echo "For more information, see: /home/\$USER/BirdNET-Pi/docs/TFT_SERVICE_FIX.md"
echo ""
