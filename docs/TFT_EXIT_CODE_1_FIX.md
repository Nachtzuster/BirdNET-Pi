# TFT Display Service Exit Code 1 - Troubleshooting Guide

## Problem Description

When enabling the TFT display service with `sudo systemctl enable --now tft_display.service`, the service fails with exit code 1:

```
● tft_display.service - BirdNET-Pi TFT Display Service
     Loaded: loaded (/etc/systemd/system/tft_display.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Wed 2025-12-31 16:44:13 CET; 990ms ago
 Invocation: a305a0e5bd4c46a28fcaae273382291e
    Process: 24012 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=1/FAILURE)
   Main PID: 24012 (code=exited, status=1/FAILURE)
```

## Quick Diagnosis

**FIRST STEP**: Check the actual error message in the logs:

```bash
sudo journalctl -u tft_display.service -n 50 --no-pager
```

Look for specific error messages. The most common causes are:

### Cause 1: Missing Python Libraries (Most Common)

**Error message in logs:**
```
[ERROR] Required libraries not available
[ERROR] Install with: pip install Pillow luma.lcd
```

**Solution:**
```bash
# Navigate to BirdNET-Pi directory
cd ~/BirdNET-Pi

# Activate virtual environment
source birdnet/bin/activate

# Install required packages
pip install Pillow luma.lcd luma.core

# Deactivate virtual environment
deactivate

# Restart the service
sudo systemctl restart tft_display.service

# Check status
sudo systemctl status tft_display.service
```

### Cause 2: Database Not Found

**Error message in logs:**
```
[ERROR] Database not found
```

**Solution:**
```bash
# Check if the database exists
ls -la ~/BirdNET-Pi/scripts/birds.db

# If it doesn't exist, create it
cd ~/BirdNET-Pi
bash scripts/createdb.sh

# Restart the service
sudo systemctl restart tft_display.service
```

### Cause 3: Configuration File Missing or TFT Not Enabled

**Error message in logs:**
```
[WARNING] Configuration file not found: /etc/birdnet/birdnet.conf
```
or
```
[INFO] TFT display is disabled in configuration
```

**Solution:**
```bash
# Check if config exists
ls -la /etc/birdnet/birdnet.conf

# Enable TFT in configuration
# Edit the file and add/change this line:
sudo nano /etc/birdnet/birdnet.conf

# Add or modify:
TFT_ENABLED=1
TFT_TYPE=ili9486

# Save and exit (Ctrl+O, Enter, Ctrl+X)

# Restart the service
sudo systemctl restart tft_display.service
```

## Automated Fix Script

Use the quick fix script that handles all common issues:

```bash
cd ~/BirdNET-Pi
bash scripts/quick_fix_tft.sh
```

This script will:
- ✓ Update the tft_display.py script
- ✓ Install/update required Python packages
- ✓ Restart the service
- ✓ Show you the status

## Testing Python Environment

Before enabling the service, test if all required packages are installed:

```bash
# Test using the dedicated test script
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py
```

This will show you exactly which packages are missing (if any).

## Manual Step-by-Step Troubleshooting

### Step 1: View Recent Logs

```bash
sudo journalctl -u tft_display.service -n 50 --no-pager
```

### Step 2: Check Python Can Find the Script

```bash
ls -la /usr/local/bin/tft_display.py
```

Expected output:
```
-rwxr-xr-x 1 root root 24xxx Dec 31 16:44 /usr/local/bin/tft_display.py
```

If the file doesn't exist or is a symlink:
```bash
sudo rm -f /usr/local/bin/tft_display.py
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py
```

### Step 3: Test Python Script Directly

```bash
# This will show you the exact error
~/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py
```

Press Ctrl+C to stop after you see the error message.

### Step 4: Verify Virtual Environment Has Required Packages

```bash
# Check if Pillow is installed
~/BirdNET-Pi/birdnet/bin/python3 -c "import PIL; print('PIL:', PIL.__version__)"

# Check if luma.lcd is installed
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.lcd; print('luma.lcd:', luma.lcd.__version__)"

# Check if luma.core is installed
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.core; print('luma.core:', luma.core.__version__)"
```

If any of these fail with "ModuleNotFoundError", install the missing packages:
```bash
cd ~/BirdNET-Pi
source birdnet/bin/activate
pip install Pillow luma.lcd luma.core
deactivate
```

### Step 5: Check Configuration

```bash
# View TFT-related configuration
grep "TFT_" /etc/birdnet/birdnet.conf
```

You should see at least:
```
TFT_ENABLED=1
TFT_TYPE=ili9486
```

If not, add them:
```bash
echo "TFT_ENABLED=1" | sudo tee -a /etc/birdnet/birdnet.conf
echo "TFT_TYPE=ili9486" | sudo tee -a /etc/birdnet/birdnet.conf
```

### Step 6: Check Database Exists

```bash
ls -la ~/BirdNET-Pi/scripts/birds.db
```

If it doesn't exist, create it:
```bash
cd ~/BirdNET-Pi
bash scripts/createdb.sh
```

## Expected Successful Startup

When the service starts successfully, you should see these logs:

```bash
sudo journalctl -u tft_display.service -f
```

Expected output:
```
[INFO] BirdNET-Pi TFT Display starting...
[INFO] Configuration loaded successfully
[INFO] TFT Enabled: True
[INFO] Display Type: ili9486
[INFO] Rotation: 90°
[INFO] Found database at: /home/yves/BirdNET-Pi/scripts/birds.db
[INFO] Initializing display...
[INFO] Display initialized: 320x480 (ili9486)
[INFO] Font loaded: DejaVuSans.ttf (12pt)
[INFO] Entering main display loop
[INFO] Initial update: X detections loaded
```

## Debian Trixie Specific Notes

The user asked if something needs to be installed in Debian Trixie itself. The answer is **NO** - the error is not related to missing Debian packages.

The TFT display service uses:
- **Python packages** (installed in virtual environment): `Pillow`, `luma.lcd`, `luma.core`
- **System packages** (already installed by install_tft.sh): `python3-dev`, `libfreetype-dev`, etc.
- **Kernel drivers**: Loaded automatically when dtoverlay is configured in `/boot/firmware/config.txt`

The exit code 1 is almost always due to missing Python packages in the virtual environment, not missing Debian system packages.

## Still Not Working?

If you've tried all the above and the service still fails:

1. **Collect diagnostic information:**
   ```bash
   # Save logs to a file
   sudo journalctl -u tft_display.service -n 100 --no-pager > ~/tft_logs.txt
   
   # Test hardware
   bash ~/BirdNET-Pi/scripts/test_tft_hardware.sh > ~/tft_hardware.txt 2>&1
   
   # Test Python environment
   ~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py > ~/tft_python.txt 2>&1
   
   # Check configuration
   grep "TFT_" /etc/birdnet/birdnet.conf > ~/tft_config.txt
   ```

2. **Review the collected files:**
   - `~/tft_logs.txt` - Service logs
   - `~/tft_hardware.txt` - Hardware detection results
   - `~/tft_python.txt` - Python package test results
   - `~/tft_config.txt` - TFT configuration

3. **Share the diagnostic information** when asking for help, along with:
   - Raspberry Pi model
   - Debian version: `cat /etc/os-release | grep VERSION`
   - TFT display model (e.g., ILI9486)

## Related Documentation

- [TFT_SERVICE_FIX.md](TFT_SERVICE_FIX.md) - Previous service fix for similar issues
- [UPDATE_INSTRUCTIES.md](UPDATE_INSTRUCTIES.md) - Update instructions in Dutch
- [TFT_TESTING_GUIDE.md](TFT_TESTING_GUIDE.md) - Comprehensive testing procedures
- [TFT_DEEP_TROUBLESHOOT.md](TFT_DEEP_TROUBLESHOOT.md) - Deep troubleshooting for hardware issues

## Quick Reference Commands

```bash
# View service status
sudo systemctl status tft_display.service

# View recent logs
sudo journalctl -u tft_display.service -n 50 --no-pager

# View live logs (Ctrl+C to exit)
sudo journalctl -u tft_display.service -f

# Restart service
sudo systemctl restart tft_display.service

# Test Python environment
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py

# Run quick fix script
cd ~/BirdNET-Pi && bash scripts/quick_fix_tft.sh
```
