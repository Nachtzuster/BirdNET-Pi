# TFT Screen Testing Guide

## Quick Start Testing on Raspberry Pi 4B with Trixie

### Pre-Installation Test (System Check)
```bash
# Navigate to scripts directory
cd ~/BirdNET-Pi/scripts

# Run detection (before installation)
./detect_tft.sh
```

**Expected Result**: Should show "NOT FOUND" for TFT/XPT2046 if not yet configured.

---

### Installation Test

#### 1. Run Installation
```bash
cd ~/BirdNET-Pi/scripts
./install_tft.sh
```

**What to test**:
- [ ] Script creates backup directory at `~/BirdNET-Pi/tft_backups`
- [ ] Script backs up `/boot/firmware/config.txt`
- [ ] Script backs up `/etc/birdnet/birdnet.conf`
- [ ] Package installation completes without errors
- [ ] Display type selection works (choose your display type)
- [ ] Script adds TFT configuration to birdnet.conf
- [ ] Script prompts for reboot

#### 2. Verify Backups
```bash
ls -la ~/BirdNET-Pi/tft_backups/
```

**Expected**: Should show timestamped backup files:
- `config.txt.YYYYMMDD_HHMMSS`
- `birdnet.conf.YYYYMMDD_HHMMSS`
- `last_backup.txt`

#### 3. Reboot
```bash
sudo reboot
```

---

### Post-Installation Test

#### 1. Verify TFT Detection
```bash
cd ~/BirdNET-Pi/scripts
./detect_tft.sh
```

**Expected Results**:
- ✅ SPI enabled: YES
- ✅ XPT2046 touch controller: FOUND (if hardware connected)
- ✅ SPI TFT Display: FOUND (if hardware connected)
- ✅ Framebuffer devices: Multiple devices (/dev/fb0, /dev/fb1)

#### 2. Check Configuration
```bash
cat /etc/birdnet/birdnet.conf | grep "^TFT_"
```

**Expected Output**:
```
TFT_ENABLED=0
TFT_DEVICE=/dev/fb1
TFT_ROTATION=90
TFT_FONT_SIZE=12
TFT_SCROLL_SPEED=2
TFT_MAX_DETECTIONS=20
TFT_UPDATE_INTERVAL=5
TFT_TYPE=ili9341
```

#### 3. Enable TFT Display
```bash
sudo nano /etc/birdnet/birdnet.conf
```

Change `TFT_ENABLED=0` to `TFT_ENABLED=1`, save and exit.

#### 4. Enable and Start Service
```bash
sudo systemctl enable tft_display.service
sudo systemctl start tft_display.service
```

#### 5. Check Service Status
```bash
sudo systemctl status tft_display.service
```

**Expected**: Service should be "active (running)"

#### 6. Monitor Service Logs
```bash
journalctl -u tft_display.service -f
```

**Expected Log Output** (with TFT connected):
```
BirdNET-Pi TFT Display starting...
Configuration loaded successfully
TFT Enabled: True
Display Type: ili9341
Rotation: 90°
Display initialized: 240x320
Loaded font: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
Entering main display loop
Updated display with X detections
```

**Expected Log Output** (without TFT - fallback mode):
```
BirdNET-Pi TFT Display starting...
Configuration loaded successfully
TFT Enabled: True
Failed to initialize display. Running in fallback mode.
Display will not be available, but service will continue running.
TFT Display daemon stopped (fallback mode)
```

---

### Fallback Test (Without TFT Hardware)

**Purpose**: Verify system continues working even without TFT connected.

#### 1. Enable TFT without hardware
```bash
sudo nano /etc/birdnet/birdnet.conf
# Set TFT_ENABLED=1
sudo systemctl start tft_display.service
```

#### 2. Verify graceful fallback
```bash
sudo systemctl status tft_display.service
journalctl -u tft_display.service -n 50
```

**Expected**:
- Service should exit gracefully (exit code 0)
- Log message: "Running in fallback mode"
- System continues normal operation
- HDMI output unaffected

#### 3. Verify BirdNET-Pi still works
```bash
sudo systemctl status birdnet_analysis.service
sudo systemctl status birdnet_recording.service
```

**Expected**: All core services running normally.

---

### Display Functionality Test (With TFT Hardware)

#### 1. Physical Display Check
- [ ] TFT screen powers on
- [ ] Backlight visible
- [ ] Text displayed clearly
- [ ] Portrait orientation (90° or 270°)

#### 2. Content Display Check
- [ ] Title "BirdNET-Pi Detections" visible at top
- [ ] Separator line below title
- [ ] Species names displayed
- [ ] Confidence scores displayed (with %)
- [ ] Timestamp at bottom
- [ ] Text scrolls upward

#### 3. HDMI Output Check
- [ ] HDMI monitor still displays output
- [ ] Web interface accessible
- [ ] No performance degradation on HDMI

#### 4. Database Integration
```bash
# Trigger a test detection or wait for natural detection
# Watch logs
journalctl -u tft_display.service -f
```

**Expected**: Log should show "Updated display with N detections"

---

### Orientation Test

#### 1. Test Different Rotations
```bash
sudo nano /etc/birdnet/birdnet.conf
```

Change `TFT_ROTATION` to:
- `0` (landscape)
- `90` (portrait right)
- `180` (landscape inverted)
- `270` (portrait left)

After each change:
```bash
sudo systemctl restart tft_display.service
```

Verify display orientation matches setting.

---

### Performance Test

#### 1. Monitor CPU Usage
```bash
# Watch CPU usage
top -p $(pgrep -f tft_display.py)
```

**Expected**: Low CPU usage (<5% on average)

#### 2. Check Memory Usage
```bash
ps aux | grep tft_display.py
```

**Expected**: Memory usage <50MB

#### 3. Verify No Impact on Core Services
```bash
# Monitor analysis service
sudo systemctl status birdnet_analysis.service

# Check detection rate
tail -f ~/BirdNET-Pi/scripts/*.txt
```

**Expected**: No change in detection performance

---

### Rollback Test

#### 1. Run Rollback Script
```bash
cd ~/BirdNET-Pi/scripts
./rollback_tft.sh
```

**What to test**:
- [ ] Script lists available backups
- [ ] Script stops TFT service
- [ ] Script disables TFT service
- [ ] Script restores configuration files
- [ ] Script removes service files
- [ ] Script offers to remove Python packages
- [ ] Script offers to remove backups
- [ ] Script prompts for reboot

#### 2. Verify Rollback
```bash
# After reboot
./detect_tft.sh
```

**Expected**: Should show TFT not detected or not configured

#### 3. Check Configuration
```bash
cat /etc/birdnet/birdnet.conf | grep "TFT_"
```

**Expected**: No TFT_ configuration lines (or original backup restored)

#### 4. Verify Service Removed
```bash
sudo systemctl status tft_display.service
```

**Expected**: Service not found or inactive

#### 5. Verify Core Functionality
```bash
# Check main services
sudo systemctl status birdnet_analysis.service
sudo systemctl status birdnet_recording.service

# Access web interface
curl -I http://localhost/
```

**Expected**: All core functionality working normally

---

### Edge Cases to Test

#### 1. Configuration with TFT_ENABLED=0
```bash
sudo nano /etc/birdnet/birdnet.conf
# Set TFT_ENABLED=0
sudo systemctl start tft_display.service
```

**Expected**: Service exits immediately with message "TFT display is disabled"

#### 2. Missing Database
```bash
# Temporarily rename database
sudo mv ~/BirdNET-Pi/scripts/birds.db ~/BirdNET-Pi/scripts/birds.db.bak
sudo systemctl restart tft_display.service
journalctl -u tft_display.service -n 20
```

**Expected**: Service logs "Database not found" error but continues or exits gracefully

Don't forget to restore:
```bash
sudo mv ~/BirdNET-Pi/scripts/birds.db.bak ~/BirdNET-Pi/scripts/birds.db
```

#### 3. Invalid Display Type
```bash
sudo nano /etc/birdnet/birdnet.conf
# Set TFT_TYPE=invalid_display
sudo systemctl restart tft_display.service
```

**Expected**: Service logs error and enters fallback mode

---

## Test Checklist Summary

### Installation Phase
- [ ] Detection script runs successfully
- [ ] Installation completes without errors
- [ ] Backups created properly
- [ ] Configuration added to birdnet.conf
- [ ] Post-reboot TFT detected

### Functionality Phase
- [ ] Service starts successfully
- [ ] Display shows content (if hardware present)
- [ ] Scrolling works properly
- [ ] Portrait orientation correct
- [ ] HDMI still works simultaneously
- [ ] Low performance impact

### Fallback Phase
- [ ] Service handles missing hardware gracefully
- [ ] Core BirdNET-Pi unaffected without TFT
- [ ] Clear log messages in fallback mode

### Rollback Phase
- [ ] Rollback script completes successfully
- [ ] Configuration restored
- [ ] Service removed/disabled
- [ ] System returns to original state
- [ ] No residual TFT configuration

---

## Troubleshooting Common Issues

### Issue: TFT not detected after installation
**Solution**: 
1. Check `/boot/firmware/config.txt` has correct overlays
2. Verify SPI enabled: `dtparam=spi=on`
3. Reboot again
4. Check dmesg: `sudo dmesg | grep -i spi`

### Issue: Service fails to start
**Solution**:
1. Check logs: `journalctl -u tft_display.service -n 50`
2. Verify Python virtual environment: `ls ~/BirdNET-Pi/birdnet/bin/python3`
3. Check dependencies: `source ~/BirdNET-Pi/birdnet/bin/activate && pip list | grep -i luma`

### Issue: Display shows garbled content
**Solution**:
1. Try different `TFT_ROTATION` values
2. Verify correct `TFT_TYPE` in configuration
3. Check display wiring matches documentation

### Issue: Touch not responding
**Solution**:
1. Verify XPT2046 overlay in config.txt
2. Test with: `sudo evtest`
3. Check interrupt pin configuration

---

## Quick Commands Reference

```bash
# Detection
./detect_tft.sh

# Installation
./install_tft.sh

# Enable service
sudo systemctl enable tft_display.service
sudo systemctl start tft_display.service

# Check status
sudo systemctl status tft_display.service

# View logs
journalctl -u tft_display.service -f

# Restart service
sudo systemctl restart tft_display.service

# Rollback
./rollback_tft.sh

# Check config
cat /etc/birdnet/birdnet.conf | grep "^TFT_"
```

---

## Success Criteria

✅ **Minimum Viable Product**:
- Installation completes without errors
- Service starts and runs (even in fallback mode)
- No impact on existing BirdNET-Pi functionality
- Rollback works correctly

✅ **Full Functionality** (with hardware):
- TFT displays bird detections
- Portrait orientation correct
- Scrolling smooth
- HDMI works simultaneously
- Low performance impact

✅ **Production Ready**:
- All edge cases handled gracefully
- Clear error messages
- Documentation complete
- No security issues
- Easy to troubleshoot
