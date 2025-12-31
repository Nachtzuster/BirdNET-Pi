# TFT Display Service Fix - Exit Code 1 Error

## Problem Description

The `tft_display.service` was failing with exit code 1 because the Python script was not installed to the correct location.

### Error Symptoms

```
● tft_display.service - BirdNET-Pi TFT Display Service
     Loaded: loaded (/etc/systemd/system/tft_display.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Wed 2025-12-31 13:00:14 CET; 5s ago
 Invocation: 63042d1f449c4cbdae88179253839805
    Process: 3095 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=1/FAILURE)
   Main PID: 3095 (code=exited, status=1/FAILURE)
        CPU: 376ms
```

## Root Cause

The service file referenced `/usr/local/bin/tft_display.py`, but the installation scripts never copied or linked the script to that location. The script only existed at `~/BirdNET-Pi/scripts/tft_display.py`.

## Solution

This fix updates all installation scripts to properly install the TFT display script to `/usr/local/bin/`:

1. **install_services.sh** - Copies script during initial installation
2. **install_tft_service.sh** - Copies script when TFT service is installed via web interface
3. **update_birdnet_snippets.sh** - Updates script during system updates
4. **rollback_tft.sh** - Removes script during rollback

## How to Apply This Fix

### Option 1: Update via Git (Recommended)

If you already have BirdNET-Pi installed with the TFT display:

```bash
# Navigate to your BirdNET-Pi directory
cd ~/BirdNET-Pi

# Fetch the latest changes
git fetch origin

# Check out this fix branch
git checkout copilot/fix-tft-display-service-error

# Or merge it into your current branch
git merge copilot/fix-tft-display-service-error

# Run the update script (this will install the script to /usr/local/bin)
sudo ~/BirdNET-Pi/scripts/update_birdnet_snippets.sh

# Restart the TFT display service
sudo systemctl restart tft_display.service

# Check the status
sudo systemctl status tft_display.service
```

### Option 2: Manual Installation

If you want to manually apply the fix without updating:

```bash
# Copy the script to /usr/local/bin
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py

# Make it executable
sudo chmod +x /usr/local/bin/tft_display.py

# Restart the service
sudo systemctl restart tft_display.service

# Check the status
sudo systemctl status tft_display.service
```

### Option 3: Reinstall TFT Service

If you prefer to reinstall the service completely:

```bash
# Stop and disable the service
sudo systemctl stop tft_display.service
sudo systemctl disable tft_display.service

# Remove old service files
sudo rm -f /usr/lib/systemd/system/tft_display.service
sudo rm -f ~/BirdNET-Pi/templates/tft_display.service

# Update to the latest code
cd ~/BirdNET-Pi
git fetch origin
git checkout copilot/fix-tft-display-service-error

# Reinstall the service
~/BirdNET-Pi/scripts/install_tft_service.sh

# Enable and start the service
sudo systemctl enable --now tft_display.service

# Check the status
sudo systemctl status tft_display.service
```

## Verification

After applying the fix, verify that everything is working:

```bash
# 1. Check that the script is installed
ls -la /usr/local/bin/tft_display.py
# Should show: -rwxr-xr-x ... /usr/local/bin/tft_display.py

# 2. Check service status
sudo systemctl status tft_display.service
# Should show: Active: active (running) or Active: activating

# 3. Check logs
sudo journalctl -u tft_display.service -f
# Should show startup messages without errors

# 4. Test the script directly
/usr/local/bin/tft_display.py
# Should start without "file not found" errors
# Press Ctrl+C to stop
```

## Expected Behavior After Fix

1. **Service starts successfully** - No more exit code 1 errors
2. **Script runs in standby mode** if TFT is disabled in configuration
3. **Display initializes** if TFT is enabled and hardware is present
4. **Graceful fallback** if hardware is not present (service stays running)

## Troubleshooting

### Issue: Service still fails after applying fix

**Solution:**
```bash
# Check if the script is in the right place
ls -la /usr/local/bin/tft_display.py

# If not present, copy it manually
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl restart tft_display.service
```

### Issue: Permission denied errors

**Solution:**
```bash
# Ensure the script has correct permissions
sudo chmod +x /usr/local/bin/tft_display.py

# Ensure the service runs as the correct user
grep "User=" /usr/lib/systemd/system/tft_display.service
# Should show your username, not root
```

### Issue: Python module not found errors

**Solution:**
```bash
# Install required Python packages
source ~/BirdNET-Pi/birdnet/bin/activate
pip install luma.lcd luma.core Pillow

# Restart the service
sudo systemctl restart tft_display.service
```

## Additional Notes

### About Debian Trixie

The user asked if something needs to be installed in Debian Trixie itself. The answer is:

**System packages** are installed by the `install_tft.sh` script:
- `build-essential`
- `cmake`
- `git`
- `evtest`
- `python3-dev`
- `python3-pip`
- `libfreetype-dev`
- `libjpeg-dev`
- `libopenjp2-7`
- `libtiff6`

**Python packages** are installed in the BirdNET-Pi virtual environment:
- `luma.lcd`
- `luma.core`
- `Pillow`

The fix does not require additional Debian Trixie system packages.

### About the Framebuffer

The user asked if the issue was related to not using the second framebuffer (/dev/fb1).

**Answer:** The code does reference `/dev/fb1` for **auto-detection** of display size, but it doesn't directly write to the framebuffer. The `luma.lcd` library handles the actual display communication through SPI, which is the correct approach for these TFT displays.

The framebuffer references are only used for:
1. Auto-detecting screen resolution
2. Falling back to device type defaults if detection fails

This is working as designed and was not the cause of the exit code 1 error.

## Related Documentation

- [TFT_SCREEN_SETUP.md](TFT_SCREEN_SETUP.md) - Complete setup guide
- [TFT_TESTING_GUIDE.md](TFT_TESTING_GUIDE.md) - Testing procedures
- [TFT_AUTO_CONFIGURATION.md](TFT_AUTO_CONFIGURATION.md) - Auto-configuration details

## Questions?

If you still experience issues after applying this fix, please provide:
1. Output of `sudo systemctl status tft_display.service`
2. Output of `sudo journalctl -u tft_display.service -n 50`
3. Output of `ls -la /usr/local/bin/tft_display.py`
4. Your Raspberry Pi model and Debian version
