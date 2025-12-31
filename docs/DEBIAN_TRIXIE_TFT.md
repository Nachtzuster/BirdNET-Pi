# Debian Trixie vs Bookworm - TFT Display Requirements

## Executive Summary

**Good news**: No new packages are required for Debian Trixie compared to Bookworm for TFT display support. The same dependencies work on both versions.

## Package Comparison

### System Packages (Unchanged)

Both Debian Bookworm (12) and Trixie (13) require the same system packages:

```bash
# Build tools
build-essential
cmake
git

# Python development
python3
python3-pip
python3-dev

# Image libraries
libfreetype6      # or libfreetype-dev
libjpeg62-turbo   # or libjpeg-dev
libopenjp2-7
libtiff6

# Optional but recommended
evtest            # For touch screen testing
```

### Python Packages (Unchanged)

The same Python packages work on both:

```bash
pip install luma.lcd luma.core Pillow
```

## Key Differences in Debian Trixie

### 1. Boot Configuration Location

**Bookworm**: `/boot/config.txt`
**Trixie**: `/boot/firmware/config.txt`

Our scripts already handle this correctly by checking for `/boot/firmware/config.txt` first.

### 2. Python Version

**Bookworm**: Python 3.11
**Trixie**: Python 3.12

This doesn't affect luma.lcd or Pillow - both work fine with Python 3.12.

### 3. Systemd Changes

Minor improvements in systemd, but no changes affecting our service files. The service file syntax remains the same.

### 4. GPIO Access

No changes - GPIO access works the same way via `/sys/class/gpio` and device tree overlays.

### 5. SPI Kernel Module

No changes - `spi_bcm2835` module works the same way.

## Verification

The scripts in this repository have been tested and work on both:
- Debian Bookworm (12)
- Debian Trixie (13)

## Known Issues and Solutions

### Issue 1: Virtual Environment Python Packages

**Problem**: Even if packages are installed system-wide, BirdNET-Pi uses a virtual environment.

**Solution**: Install packages in the virtual environment:
```bash
source ~/BirdNET-Pi/birdnet/bin/activate
pip install luma.lcd luma.core Pillow
deactivate
```

Or run the install script which does this automatically:
```bash
~/BirdNET-Pi/scripts/install_tft.sh
```

### Issue 2: Permission Errors

**Problem**: SPI and GPIO access may be denied for non-root users.

**Solution**: Add user to appropriate groups:
```bash
sudo usermod -a -G gpio,spi $USER
# Log out and back in for changes to take effect
```

### Issue 3: Missing Device Tree Overlay

**Problem**: TFT display not detected even with correct drivers.

**Solution**: Add appropriate overlay to `/boot/firmware/config.txt`:

For ILI9341:
```
dtparam=spi=on
dtoverlay=piscreen,speed=16000000,rotate=90
```

For ILI9486:
```
dtparam=spi=on
dtoverlay=waveshare35a,speed=16000000,rotate=90
```

For ST7735:
```
dtparam=spi=on
dtoverlay=piscreen2r,speed=16000000,rotate=90
```

Then reboot.

## Testing Commands

### Check Debian Version
```bash
cat /etc/debian_version
# Should show: 13.x or "trixie/sid"
```

### Check Python Version
```bash
python3 --version
# Should show: Python 3.12.x
```

### Check Boot Config Location
```bash
ls -la /boot/firmware/config.txt
```

### Check SPI
```bash
ls -l /dev/spidev*
# Should show /dev/spidev0.0 and possibly spidev0.1
```

### Check Framebuffer
```bash
ls -l /dev/fb*
# Should show /dev/fb0 (HDMI) and /dev/fb1 (TFT if configured)
```

### Test Python Packages
```bash
# System Python
python3 -c "import luma.lcd; print('OK')"

# Virtual environment (if BirdNET-Pi installed)
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.lcd; print('OK')"
```

## References

### Official Documentation

- [Debian Trixie Release Notes](https://www.debian.org/releases/trixie/)
- [Raspberry Pi OS Documentation](https://www.raspberrypi.com/documentation/)
- [luma.lcd Documentation](https://luma-lcd.readthedocs.io/)

### Device Tree Overlays

The device tree overlays are provided by the Raspberry Pi kernel and have not changed between Bookworm and Trixie. Available overlays can be listed with:

```bash
ls /boot/firmware/overlays/*tft* /boot/firmware/overlays/*ili* /boot/firmware/overlays/*st7*
```

Common ones:
- `piscreen.dtbo` - ILI9341 (Adafruit PiTFT 2.8")
- `piscreen2r.dtbo` - ST7735R (Adafruit PiTFT 1.8")
- `waveshare35a.dtbo` - ILI9486 (Waveshare 3.5" A)
- `waveshare35b.dtbo` - ILI9486 (Waveshare 3.5" B)

## Conclusion

**No new packages are required for Debian Trixie.** If you're experiencing issues, they are likely due to:

1. **Missing packages in the Python virtual environment** - Most common!
2. **Missing boot configuration** - SPI or TFT overlay not enabled
3. **Permission issues** - User not in gpio/spi groups
4. **Hardware connection** - Physical wiring problems

Use the test scripts to diagnose:
```bash
# Hardware and system test
bash ~/BirdNET-Pi/scripts/test_tft_hardware.sh

# Python packages test
python3 ~/BirdNET-Pi/scripts/test_tft_python.py

# If in BirdNET-Pi venv:
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py
```
