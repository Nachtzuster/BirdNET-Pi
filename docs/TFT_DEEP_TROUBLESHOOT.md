# TFT Display Service Exit Code 1 - Deep Dive Troubleshooting

## Understanding the Error

When you see:
```
Process: 3129 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=1/FAILURE)
```

This means the Python script `/usr/local/bin/tft_display.py` started but exited with code 1 (error).

## Root Causes (in order of likelihood)

### 1. Python Packages Missing from Virtual Environment ⭐ MOST COMMON

**Symptom**: Service exits immediately with code 1

**Diagnosis**:
```bash
# Test if packages are in the virtual environment
~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.lcd; print('OK')"
```

If this fails with `ModuleNotFoundError`, packages are missing.

**Fix**:
```bash
# Activate virtual environment
source ~/BirdNET-Pi/birdnet/bin/activate

# Install required packages
pip install luma.lcd luma.core Pillow

# Verify installation
python -c "import luma.lcd; import PIL; print('All packages installed')"

# Deactivate
deactivate

# Restart service
sudo systemctl restart tft_display.service
```

**Why this happens**: 
- System Python may have the packages, but BirdNET-Pi uses its own virtual environment
- The service runs: `/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py`
- This Python interpreter needs its own copy of the packages

### 2. Script Not Installed to /usr/local/bin

**Symptom**: Service can't find the script

**Diagnosis**:
```bash
ls -la /usr/local/bin/tft_display.py
```

If this shows "No such file or directory", the script wasn't installed.

**Fix**:
```bash
# Copy script manually
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py

# Restart service
sudo systemctl restart tft_display.service
```

### 3. Configuration File Issues

**Symptom**: Service exits after checking configuration

**Diagnosis**:
```bash
# Check if config exists
ls -la /etc/birdnet/birdnet.conf

# Check TFT settings
grep TFT /etc/birdnet/birdnet.conf
```

**What to look for**:
- `TFT_ENABLED=1` - Service will enter standby mode if 0
- If TFT_ENABLED=1 but libraries are missing, service exits with code 1

**Fix**:
If TFT should be disabled:
```bash
sudo nano /etc/birdnet/birdnet.conf
# Change TFT_ENABLED=1 to TFT_ENABLED=0
# Save and exit

sudo systemctl restart tft_display.service
```

If TFT should be enabled, ensure packages are installed (see #1).

### 4. Virtual Environment Doesn't Exist

**Symptom**: Service can't find Python interpreter

**Diagnosis**:
```bash
ls -la ~/BirdNET-Pi/birdnet/bin/python3
```

If not found, virtual environment is missing.

**Fix**:
```bash
# Reinstall BirdNET-Pi or recreate venv
cd ~/BirdNET-Pi
python3 -m venv birdnet
source birdnet/bin/activate
pip install -r requirements.txt
pip install luma.lcd luma.core Pillow
deactivate
```

### 5. Permission Issues

**Symptom**: Service starts but can't access SPI/GPIO

**Diagnosis**:
```bash
# Check service user
grep "User=" /usr/lib/systemd/system/tft_display.service

# Check if that user is in required groups
groups $(grep "User=" /usr/lib/systemd/system/tft_display.service | cut -d= -f2)
```

**Fix**:
```bash
# Add user to required groups (replace USERNAME)
sudo usermod -a -G gpio,spi USERNAME

# Or run service as root (not recommended but works for testing)
sudo systemctl edit tft_display.service

# Add:
# [Service]
# User=root
# Group=root

sudo systemctl daemon-reload
sudo systemctl restart tft_display.service
```

## Step-by-Step Diagnosis Procedure

### Step 1: Check Service Status
```bash
sudo systemctl status tft_display.service
```

Look for:
- "code=exited, status=1/FAILURE" - Script exited with error
- "code=exited, status=0/SUCCESS" - Normal exit (should restart)
- "activating (auto-restart)" - Repeatedly failing

### Step 2: Check Recent Logs
```bash
sudo journalctl -u tft_display.service -n 50 --no-pager
```

Look for:
- "Required libraries not available" - Missing Python packages ⭐
- "Configuration file not found" - Missing config
- "TFT display is disabled" - Standby mode (not an error)
- "Failed to initialize display" - Hardware or driver issue
- Python traceback - Specific error

### Step 3: Test Script Manually
```bash
# Test with the same Python the service uses
~/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py
```

This will show the actual error message. Press Ctrl+C to stop.

### Step 4: Test Package Imports
```bash
# Test in virtual environment
~/BirdNET-Pi/birdnet/bin/python3 << 'EOF'
try:
    import luma.lcd
    print("✓ luma.lcd OK")
except ImportError as e:
    print(f"✗ luma.lcd: {e}")

try:
    import luma.core
    print("✓ luma.core OK")
except ImportError as e:
    print(f"✗ luma.core: {e}")

try:
    import PIL
    print("✓ Pillow OK")
except ImportError as e:
    print(f"✗ Pillow: {e}")
EOF
```

### Step 5: Use Test Scripts
```bash
# Full hardware test
bash ~/BirdNET-Pi/scripts/test_tft_hardware.sh

# Python packages test
~/BirdNET-Pi/birdnet/bin/python3 ~/BirdNET-Pi/scripts/test_tft_python.py
```

## Quick Fix Script

Save this as `fix_tft_service.sh` and run it:

```bash
#!/bin/bash
set -e

echo "=== TFT Service Quick Fix ==="
echo ""

# Fix 1: Ensure script is installed
echo "1. Installing script to /usr/local/bin..."
if [ -f ~/BirdNET-Pi/scripts/tft_display.py ]; then
    sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
    sudo chmod +x /usr/local/bin/tft_display.py
    echo "   ✓ Script installed"
else
    echo "   ✗ Source script not found!"
    exit 1
fi

# Fix 2: Install Python packages in venv
echo ""
echo "2. Installing Python packages in virtual environment..."
if [ -d ~/BirdNET-Pi/birdnet ]; then
    source ~/BirdNET-Pi/birdnet/bin/activate
    pip install --upgrade pip
    pip install luma.lcd luma.core Pillow
    deactivate
    echo "   ✓ Packages installed"
else
    echo "   ✗ Virtual environment not found!"
    exit 1
fi

# Fix 3: Verify installation
echo ""
echo "3. Verifying installation..."
if ~/BirdNET-Pi/birdnet/bin/python3 -c "import luma.lcd; import PIL" 2>/dev/null; then
    echo "   ✓ All packages importable"
else
    echo "   ✗ Package import failed!"
    exit 1
fi

# Fix 4: Restart service
echo ""
echo "4. Restarting service..."
sudo systemctl daemon-reload
sudo systemctl restart tft_display.service
sleep 2

# Check status
echo ""
echo "5. Checking service status..."
if sudo systemctl is-active --quiet tft_display.service; then
    echo "   ✓ Service is running"
else
    echo "   Status:"
    sudo systemctl status tft_display.service --no-pager -l
fi

echo ""
echo "=== Done ==="
echo ""
echo "Check logs with: sudo journalctl -u tft_display.service -f"
```

Make it executable and run:
```bash
chmod +x fix_tft_service.sh
./fix_tft_service.sh
```

## Still Not Working?

If after all this the service still fails:

1. **Capture full logs**:
   ```bash
   sudo journalctl -u tft_display.service -n 100 --no-pager > ~/tft_service_logs.txt
   ```

2. **Run script directly** and capture output:
   ```bash
   ~/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py 2>&1 | tee ~/tft_direct_run.txt
   # Press Ctrl+C after a few seconds
   ```

3. **Check Python environment**:
   ```bash
   ~/BirdNET-Pi/birdnet/bin/python3 -m pip list | grep -E 'luma|Pillow' > ~/python_packages.txt
   ```

4. **Check system info**:
   ```bash
   uname -a > ~/system_info.txt
   cat /etc/debian_version >> ~/system_info.txt
   cat /proc/device-tree/model >> ~/system_info.txt
   ```

Share these files for further diagnosis.
