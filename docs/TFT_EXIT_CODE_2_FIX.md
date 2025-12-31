# TFT Display Service Exit Code 2 - Solution

## Problem Description

After performing a `git pull` without restarting the system, and then enabling the TFT display service via "Tools → Services → TFT Display - Enable" in the web interface, the service fails with exit code 2:

```
● tft_display.service - BirdNET-Pi TFT Display Service
     Loaded: loaded (/etc/systemd/system/tft_display.service; enabled; preset: enabled)
     Active: activating (auto-restart) (Result: exit-code) since Wed 2025-12-31 18:44:12 CET; 1s ago
 Invocation: fa0ab4ca1ea14be5af0a25579d6a2d71
    Process: 33777 ExecStart=/home/yves/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/tft_display.py (code=exited, status=2)
   Main PID: 33777 (code=exited, status=2)
        CPU: 74ms
```

## What Does Exit Code 2 Mean?

Exit code 2 from Python typically indicates:
- **File error**: The Python script doesn't exist or isn't readable
- **Stale script**: The script at `/usr/local/bin/tft_display.py` is an old version that isn't compatible
- **Import error**: A critical module cannot be imported (very rare)

## Root Cause

When you do a `git pull`, the code in the repository `~/BirdNET-Pi/scripts/tft_display.py` is updated. However, the TFT service uses a copy of this script installed at `/usr/local/bin/tft_display.py`. This copy is **not automatically updated** when you only click "Enable" in the web interface.

The process is:
1. ✅ `git pull` updates `~/BirdNET-Pi/scripts/tft_display.py`
2. ❌ `/usr/local/bin/tft_display.py` remains the old version
3. ❌ Service tries to start the old version → exit code 2

## Solution

This fix adds a **wrapper script** that automatically checks if the TFT display script is up-to-date before the service starts. This means that after a `git pull` and enabling the service via the web interface, the script is automatically updated.

### What Changed?

1. **New wrapper script**: `tft_display_wrapper.sh`
   - Checks if `/usr/local/bin/tft_display.py` is up-to-date
   - Automatically updates the script if needed
   - Then starts the TFT display script

2. **Service file modified**: The service now uses the wrapper script:
   ```
   ExecStart=/usr/local/bin/tft_display_wrapper.sh
   ```
   
3. **Update scripts modified**: 
   - `install_services.sh`
   - `install_tft_service.sh`
   - `update_birdnet_snippets.sh`
   
   All scripts now install both the Python script and the wrapper script.

### How to Use the Fix

#### For Existing Installations

If you already have the TFT service installed and are getting exit code 2:

```bash
# 1. Get the latest code
cd ~/BirdNET-Pi
git pull

# 2. Update the scripts (this installs the new wrapper)
sudo ~/BirdNET-Pi/scripts/update_birdnet_snippets.sh

# 3. Reload systemd to load the new service configuration
sudo systemctl daemon-reload

# 4. Restart the service
sudo systemctl restart tft_display.service

# 5. Check the status
sudo systemctl status tft_display.service
```

#### For New Installations

For new installations, everything works automatically:
1. Install via web interface: "Tools → Services → TFT Display → Install TFT Support"
2. Enable the service via the "Enable" button
3. The wrapper script ensures everything is up-to-date

### What Does the Wrapper Script Do?

The wrapper script (`tft_display_wrapper.sh`) performs the following checks:

1. **Checks if repository script exists**
   ```bash
   if [ ! -f "$REPO_SCRIPT" ]; then
       echo "ERROR: Repository script not found"
       exit 1
   fi
   ```

2. **Compares timestamps**
   ```bash
   if [ "$REPO_SCRIPT" -nt "$TARGET_SCRIPT" ]; then
       echo "Repository script is newer, will update"
       # Update script...
   fi
   ```

3. **Updates script if needed**
   - Copies new version via a temporary file
   - Moves to `/usr/local/bin/tft_display.py`
   - Sets execute permissions

4. **Starts the Python script**
   ```bash
   exec "$PYTHON" "$TARGET_SCRIPT"
   ```

### Benefits of This Solution

✅ **Automatic**: No manual steps needed after git pull
✅ **Safe**: Uses temporary files to avoid conflicts
✅ **Clear**: Logs show when an update occurs
✅ **Backwards compatible**: Works with existing installations
✅ **Reliable**: Checks all conditions before starting

### Checking Logs

To see what the wrapper script does:

```bash
sudo journalctl -u tft_display.service -n 100 --no-pager
```

You should see:
```
[2025-12-31 18:44:12] Updating TFT display script from repository...
[2025-12-31 18:44:12] TFT display script updated successfully
[2025-12-31 18:44:12] Using Python from virtual environment: /home/yves/BirdNET-Pi/birdnet/bin/python3
[2025-12-31 18:44:12] Starting TFT display service...
[2025-12-31 18:44:12] [tft_display] [INFO] BirdNET-Pi TFT Display starting...
```

## Alternative Solution (Manual)

If for some reason you don't want to use the wrapper script, you can always manually update the script:

```bash
sudo cp ~/BirdNET-Pi/scripts/tft_display.py /usr/local/bin/tft_display.py
sudo chmod +x /usr/local/bin/tft_display.py
sudo systemctl restart tft_display.service
```

## Frequently Asked Questions

**Q: Do I need to do this after every git pull?**
A: No! With the new wrapper script, the script is automatically updated when the service starts.

**Q: What if I still get exit code 2?**
A: Check the logs with `sudo journalctl -u tft_display.service -n 100`. If the wrapper script isn't installed, run `sudo ~/BirdNET-Pi/scripts/update_birdnet_snippets.sh`.

**Q: Does this affect performance?**
A: No, the check is very fast (timestamp comparison) and only happens at service start, not while running.

**Q: What if the Python virtual environment doesn't exist?**
A: The wrapper script automatically uses system Python (`/usr/bin/python3`) as a fallback.

## Summary

Exit code 2 meant that the script couldn't start, usually because `/usr/local/bin/tft_display.py` was outdated after a git pull. The new wrapper script solves this by automatically checking and updating when needed, so you no longer need to manually intervene after a code update.
