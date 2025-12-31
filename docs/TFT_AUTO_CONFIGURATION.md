# Automatic TFT Display Configuration

## Overview

BirdNET-Pi now includes **fully automatic TFT display detection and configuration**. The system automatically detects connected SPI TFT displays at boot time, configures them properly, and starts the display service without any manual intervention.

## Features

### ✅ Automatic Detection
- Detects SPI TFT displays at every system boot
- Identifies display type (ILI9341, ST7735, ST7789, ILI9488, ILI9486, etc.)
- Auto-detects screen resolution from framebuffer
- Works with touchscreen controllers (XPT2046/ADS7846)

### ✅ Automatic Configuration
- Creates and updates `/etc/birdnet/birdnet.conf` with correct settings
- Sets portrait mode orientation (90°) by default
- Configures touchscreen rotation for portrait mode
- Enables display service automatically when hardware is detected

### ✅ Intelligent Service Management
- Service stays running even when TFT is disabled (standby mode)
- Graceful fallback when display hardware fails to initialize
- Automatic retry mechanism for display initialization
- No more "activating (auto-restart)" issues

### ✅ Power Management
- Screensaver activates after 5 minutes of inactivity (configurable)
- Screen wakes on new bird detections
- Adjustable brightness levels for dim mode

## How It Works

### Boot-Time Auto-Configuration

1. **`tft_autoconfig.service`** runs at boot (before `tft_display.service`)
2. Script checks for TFT hardware presence:
   - Looks for `/dev/fb1` framebuffer device
   - Checks SPI device tree overlays
   - Scans boot configuration for TFT settings
3. If TFT detected:
   - Determines display type and resolution
   - Updates `/etc/birdnet/birdnet.conf` with `TFT_ENABLED=1`
   - Sets portrait mode rotation (90°)
   - Configures all display parameters
4. **`tft_display.service`** starts and uses the auto-configured settings

### Service Behavior

The TFT display service now has three operating modes:

#### 1. **Active Mode** (TFT_ENABLED=1, hardware present)
- Full display functionality
- Shows bird detections in scrolling list
- Screensaver after timeout
- Touch wake functionality

#### 2. **Standby Mode** (TFT_ENABLED=0)
- Service stays running but inactive
- Checks configuration every 60 seconds
- Automatically activates when enabled
- No more service restart failures

#### 3. **Fallback Mode** (hardware initialization failed)
- Service stays running for easy management
- Retries initialization up to 5 times
- Provides detailed error messages
- Allows service to be restarted easily

## Installation

### Automatic Installation (Recommended)

During BirdNET-Pi installation, TFT auto-configuration is set up automatically:

```bash
# The install_services.sh script now includes:
# - TFT display service installation
# - Auto-configuration service installation
# - Automatic hardware detection
```

### Manual Installation

If you need to install TFT support manually:

```bash
cd ~/BirdNET-Pi/scripts

# Full TFT setup (hardware drivers + auto-configuration)
./install_tft.sh

# Or just install the service components
./install_tft_service.sh
```

### Installing Auto-Configuration Only

If you already have TFT hardware configured:

```bash
cd ~/BirdNET-Pi/scripts
./install_tft_autoconfig_service.sh
```

## Configuration

### Configuration File: `/etc/birdnet/birdnet.conf`

The auto-configuration system manages these settings automatically:

```bash
# TFT Display Configuration (Auto-configured)
TFT_ENABLED=1                      # Auto-set based on hardware detection
TFT_TYPE=ili9341                   # Auto-detected display type
TFT_DEVICE=/dev/fb1                # Framebuffer device
TFT_ROTATION=90                    # Portrait mode (auto-configured)
TFT_FONT_SIZE=12                   # Text size
TFT_SCROLL_SPEED=2                 # Scroll speed (pixels per frame)
TFT_MAX_DETECTIONS=20              # Number of detections to show
TFT_UPDATE_INTERVAL=5              # Update interval in seconds
TFT_SCREENSAVER_TIMEOUT=300        # Screensaver timeout (0 to disable)
TFT_SCREENSAVER_BRIGHTNESS=0       # Screensaver brightness (0=off, 1-100=dim)
```

### Manual Configuration (Optional)

You can manually adjust settings in `/etc/birdnet/birdnet.conf`:

```bash
# Disable TFT display
TFT_ENABLED=0

# Change to landscape mode
TFT_ROTATION=0

# Adjust screensaver timeout (seconds)
TFT_SCREENSAVER_TIMEOUT=600  # 10 minutes

# Enable dim screensaver mode
TFT_SCREENSAVER_BRIGHTNESS=10  # 10% brightness

# After changes, restart the service:
sudo systemctl restart tft_display.service
```

## Testing and Verification

### Check Hardware Detection

```bash
# Run detection script manually
cd ~/BirdNET-Pi/scripts
./detect_tft.sh
```

### Run Auto-Configuration Manually

```bash
# Run auto-configuration script
sudo bash ~/BirdNET-Pi/scripts/auto_configure_tft.sh

# Check log output
cat /tmp/auto_configure_tft.log
```

### Check Service Status

```bash
# Check TFT display service
sudo systemctl status tft_display.service

# Check auto-configuration service
sudo systemctl status tft_autoconfig.service

# View logs
sudo journalctl -u tft_display.service -f
sudo journalctl -u tft_autoconfig.service
```

### Run Tests

```bash
cd ~/BirdNET-Pi

# Run bash tests
bash tests/test_tft_auto_config.sh

# Run Python tests
python3 tests/test_tft_display.py
```

## Troubleshooting

### Service Keeps Restarting

**Old Behavior:** Service would exit and restart continuously when TFT_ENABLED=0

**New Behavior:** Service stays running in standby mode

If you still see restart issues:

1. Check logs: `sudo journalctl -u tft_display.service -n 50`
2. Verify configuration: `grep TFT_ /etc/birdnet/birdnet.conf`
3. Run auto-configuration: `sudo bash ~/BirdNET-Pi/scripts/auto_configure_tft.sh`
4. Restart service: `sudo systemctl restart tft_display.service`

### Display Not Working After Reboot

1. **Check hardware connection**
   ```bash
   # Check if framebuffer device exists
   ls -l /dev/fb*
   
   # Check SPI is enabled
   ls -l /sys/class/spi_master/
   ```

2. **Verify boot configuration**
   ```bash
   # Check for TFT overlays
   grep -E "dtoverlay=(spi|tft|ili9341|st7735)" /boot/firmware/config.txt
   ```

3. **Run detection**
   ```bash
   ~/BirdNET-Pi/scripts/detect_tft.sh
   ```

4. **Check dmesg for errors**
   ```bash
   dmesg | grep -i "tft\|ili9341\|st7735\|st7789\|spi"
   ```

### Configuration Not Auto-Updating

1. **Run auto-configuration manually**
   ```bash
   sudo bash ~/BirdNET-Pi/scripts/auto_configure_tft.sh
   ```

2. **Check service is enabled**
   ```bash
   sudo systemctl is-enabled tft_autoconfig.service
   sudo systemctl status tft_autoconfig.service
   ```

3. **Re-install auto-configuration service**
   ```bash
   ~/BirdNET-Pi/scripts/install_tft_autoconfig_service.sh
   ```

### Display Shows Wrong Orientation

Auto-configuration sets portrait mode (90°) by default. To change:

```bash
# Edit configuration
sudo nano /etc/birdnet/birdnet.conf

# Change TFT_ROTATION to:
# 0   = Landscape (normal)
# 90  = Portrait (rotated right) - DEFAULT
# 180 = Landscape (upside down)
# 270 = Portrait (rotated left)

# Restart service
sudo systemctl restart tft_display.service
```

### Touch Screen Not Working

The auto-configuration should handle touch rotation automatically. If issues persist:

1. **Check touch controller detection**
   ```bash
   grep -i "xpt2046\|ads7846" /proc/bus/input/devices
   ```

2. **Verify overlay configuration**
   ```bash
   grep "ads7846" /boot/firmware/config.txt
   ```

3. **Re-run installation**
   ```bash
   ~/BirdNET-Pi/scripts/install_tft.sh
   ```

## Supported Displays

The auto-configuration system supports these display types:

| Display Type | Resolution | Auto-Detected | Notes |
|--------------|-----------|---------------|-------|
| ILI9341 | 240x320 | ✅ | Most common, cheap displays |
| ST7735/ST7735R | 128x160 | ✅ | Small displays |
| ST7789 | 240x240 | ✅ | Square displays |
| ILI9488 | 320x480 | ✅ | Larger 3.5" displays |
| ILI9486 | 320x480 | ✅ | 3.5" displays |

All displays work with XPT2046/ADS7846 touch controllers.

## Advanced Usage

### Disable Auto-Configuration

If you want to disable auto-configuration at boot:

```bash
# Disable the service
sudo systemctl disable tft_autoconfig.service

# Stop the service
sudo systemctl stop tft_autoconfig.service
```

### Custom Display Configuration

Create a custom configuration by disabling auto-configuration and manually setting values in `/etc/birdnet/birdnet.conf`.

### Multiple Displays

The system currently supports one TFT display (fb1). For multiple displays, manual configuration is required.

## Developer Information

### Files

- `scripts/auto_configure_tft.sh` - Auto-configuration script
- `scripts/install_tft_autoconfig_service.sh` - Service installer
- `scripts/tft_display.py` - Display daemon
- `scripts/detect_tft.sh` - Hardware detection utility
- `scripts/install_tft.sh` - Full TFT installation
- `tests/test_tft_auto_config.sh` - Bash tests
- `tests/test_tft_display.py` - Python tests

### Systemd Services

- `tft_autoconfig.service` - Runs at boot to detect and configure TFT
- `tft_display.service` - Main TFT display daemon

### Service Dependencies

```
tft_autoconfig.service (oneshot, runs at boot)
    ↓
tft_display.service (starts after auto-config)
    ↓
Depends on: birdnet_analysis.service
```

## Migration from Old System

If you had TFT configured before this update:

1. **Your existing configuration is preserved** - Backup created in `~/BirdNET-Pi/tft_backups/`
2. **Auto-configuration will update settings** - Old manual settings replaced with auto-detected values
3. **Service behavior changed** - No more restart loops when disabled
4. **No action required** - System upgrades automatically

If you experience issues after upgrade:

```bash
# Rollback to previous configuration
~/BirdNET-Pi/scripts/rollback_tft.sh

# Or re-install with new system
~/BirdNET-Pi/scripts/install_tft.sh
```

## Support

For issues or questions:
1. Check logs: `sudo journalctl -u tft_display.service`
2. Run tests: `bash tests/test_tft_auto_config.sh`
3. Check hardware: `~/BirdNET-Pi/scripts/detect_tft.sh`
4. Create an issue on GitHub with log output

## Summary

The new automatic TFT configuration system:
- ✅ **Eliminates manual configuration steps**
- ✅ **Prevents service restart loops**
- ✅ **Detects and configures displays automatically**
- ✅ **Works with all common SPI TFT displays**
- ✅ **Handles errors gracefully**
- ✅ **Includes comprehensive tests**

Users simply connect their TFT display, reboot, and everything works automatically!
