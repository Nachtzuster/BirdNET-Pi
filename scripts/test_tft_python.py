#!/usr/bin/env python3
"""
Simple TFT Display Test for Debian Trixie
Tests if the TFT display can be initialized and used
"""

import sys
import os

# Color codes for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def test_result(passed, message):
    """Print test result"""
    if passed:
        print(f"{GREEN}✓ PASS{NC}: {message}")
        return True
    else:
        print(f"{RED}✗ FAIL{NC}: {message}")
        return False

def main():
    print(f"{BLUE}=== Python TFT Display Test ==={NC}\n")
    
    all_passed = True
    
    # Test 1: Import PIL/Pillow
    print(f"{BLUE}Test 1: PIL/Pillow{NC}")
    try:
        from PIL import Image, ImageDraw, ImageFont
        test_result(True, "PIL/Pillow imported successfully")
        print(f"  Python: {sys.version}")
    except ImportError as e:
        test_result(False, f"PIL/Pillow import failed: {e}")
        print(f"  {YELLOW}Install with: pip install Pillow{NC}")
        all_passed = False
    print()
    
    # Test 2: Import luma.core
    print(f"{BLUE}Test 2: luma.core{NC}")
    try:
        import luma.core
        test_result(True, "luma.core imported successfully")
        print(f"  Version: {luma.core.__version__}")
    except ImportError as e:
        test_result(False, f"luma.core import failed: {e}")
        print(f"  {YELLOW}Install with: pip install luma.core{NC}")
        all_passed = False
    print()
    
    # Test 3: Import luma.lcd
    print(f"{BLUE}Test 3: luma.lcd{NC}")
    try:
        import luma.lcd
        test_result(True, "luma.lcd imported successfully")
        print(f"  Version: {luma.lcd.__version__}")
    except ImportError as e:
        test_result(False, f"luma.lcd import failed: {e}")
        print(f"  {YELLOW}Install with: pip install luma.lcd{NC}")
        all_passed = False
    print()
    
    # Test 4: Import specific display drivers
    print(f"{BLUE}Test 4: Display Drivers{NC}")
    try:
        from luma.lcd.device import ili9341, st7735, st7789v, ili9488
        test_result(True, "Standard display drivers available")
        print("  Available: ILI9341, ST7735, ST7789V, ILI9488")
        
        # Try ILI9486 (may not be in all versions)
        try:
            from luma.lcd.device import ili9486
            print("  Also available: ILI9486")
        except ImportError:
            print(f"  {YELLOW}ILI9486 not available (will use ILI9488 as fallback){NC}")
            
    except ImportError as e:
        test_result(False, f"Display driver import failed: {e}")
        all_passed = False
    print()
    
    # Test 5: Create SPI interface
    print(f"{BLUE}Test 5: SPI Interface{NC}")
    if all_passed:
        try:
            from luma.core.interface.serial import spi
            
            # Try to create SPI interface
            # This will fail if hardware is not connected, but we can catch that
            try:
                serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
                test_result(True, "SPI interface created")
                print("  Port: 0, Device: 0, DC: GPIO24, RST: GPIO25")
            except PermissionError:
                test_result(False, "Permission denied accessing SPI")
                print(f"  {YELLOW}Run as root or add user to gpio/spi groups{NC}")
                print(f"  {YELLOW}sudo usermod -a -G gpio,spi $USER{NC}")
                all_passed = False
            except FileNotFoundError as e:
                test_result(False, "SPI device not found")
                print(f"  {YELLOW}Check if /dev/spidev0.0 exists{NC}")
                print(f"  {YELLOW}Enable SPI in /boot/firmware/config.txt{NC}")
                all_passed = False
            except Exception as e:
                print(f"  {YELLOW}Warning: {e}{NC}")
                print(f"  {YELLOW}This may be expected if no TFT hardware is connected{NC}")
                
        except ImportError as e:
            test_result(False, f"SPI import failed: {e}")
            all_passed = False
    else:
        print(f"  {YELLOW}Skipping (previous tests failed){NC}")
    print()
    
    # Test 6: Try to initialize a display (will fail without hardware)
    print(f"{BLUE}Test 6: Display Initialization{NC}")
    if all_passed:
        try:
            from luma.core.interface.serial import spi
            from luma.lcd.device import ili9341
            
            print("  Attempting to initialize ILI9341 display...")
            print("  (This will fail if no hardware is connected, which is expected)")
            
            try:
                serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25)
                device = ili9341(serial, rotate=1)  # 90 degrees rotation
                test_result(True, "Display initialized successfully!")
                print(f"  Display size: {device.width}x{device.height}")
                
                # Try to draw something
                from luma.core.render import canvas
                with canvas(device) as draw:
                    draw.rectangle((0, 0, device.width, device.height), fill='black')
                    draw.text((10, 10), "Test OK", fill='white')
                
                print("  Test pattern drawn on display")
                
            except Exception as e:
                print(f"  {YELLOW}Could not initialize display: {e}{NC}")
                print(f"  {YELLOW}This is expected if no TFT hardware is connected{NC}")
                print(f"  {YELLOW}If hardware IS connected, check:{NC}")
                print(f"    - /dev/spidev0.0 exists")
                print(f"    - Wiring is correct (DC=GPIO24, RST=GPIO25)")
                print(f"    - Boot config has correct TFT overlay")
                
        except Exception as e:
            test_result(False, f"Display test failed: {e}")
            all_passed = False
    else:
        print(f"  {YELLOW}Skipping (previous tests failed){NC}")
    print()
    
    # Summary
    print(f"{BLUE}=== Summary ==={NC}\n")
    if all_passed:
        print(f"{GREEN}All software dependencies are correctly installed!{NC}")
        print()
        print("If you have TFT hardware connected and it's not working:")
        print("1. Check /dev/spidev0.0 exists: ls -l /dev/spidev*")
        print("2. Check boot config: cat /boot/firmware/config.txt | grep -E 'spi|tft'")
        print("3. Check kernel logs: dmesg | grep -i spi")
        print("4. Run the hardware test: ~/BirdNET-Pi/scripts/test_tft_hardware.sh")
    else:
        print(f"{RED}Some dependencies are missing. Install them with:{NC}")
        print()
        print("For system Python:")
        print("  pip install luma.lcd luma.core Pillow")
        print()
        print("For BirdNET-Pi virtual environment:")
        print("  source ~/BirdNET-Pi/birdnet/bin/activate")
        print("  pip install luma.lcd luma.core Pillow")
        print("  deactivate")
    print()
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
