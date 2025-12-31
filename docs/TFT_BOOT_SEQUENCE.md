# TFT Display Boot Sequence Explanation

## User Question

> "Can you activate the TFT screen during Raspberry Pi 4B boot, before BirdNET-Pi-MigCount starts?"

## Answer: This Already Happens!

The TFT screen is **ALREADY** activated during Raspberry Pi boot, **BEFORE** BirdNET-Pi starts. Here's how it works:

## Boot Sequence

### 1. Raspberry Pi Bootloader (First Phase)
```
[0s] Raspberry Pi powers on
     ↓
[1s] Bootloader reads /boot/firmware/config.txt
     ↓
```

### 2. Kernel Initialization (Second Phase)
```
[2s] Linux kernel starts
     ↓
[3s] Kernel loads device tree overlays from config.txt:
     - dtparam=spi=on           → Activate SPI interface
     - dtoverlay=waveshare35a   → Load ILI9486 TFT driver
     - dtoverlay=ads7846        → Load XPT2046 touch driver
     ↓
[4s] Hardware drivers initialize:
     - SPI bus /dev/spidev0.0 becomes available
     - TFT framebuffer /dev/fb1 created
     - Touchscreen /dev/input/eventX created
     ↓
```

### 3. Systemd Services (Third Phase)
```
[5s] Systemd starts
     ↓
[6s] Basic services start
     ↓
[7s] Network services start
     ↓
[8s] BirdNET-Pi services start:
     - birdnet_analysis.service
     - tft_display.service  ← This displays birds on screen
     ↓
```

## What Does This Mean?

### Hardware Activation (Already Happens)

The **hardware** of your TFT screen (ILI9486) is activated in **step 2** by the kernel, long before BirdNET-Pi starts.

**Configuration in `/boot/firmware/config.txt`:**
```bash
# Enable SPI (required for TFT communication)
dtparam=spi=on

# Load TFT display driver
dtoverlay=waveshare35a,speed=16000000,rotate=90

# Load touchscreen driver
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=1,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
```

These lines ensure:
1. The kernel loads the correct driver
2. The screen is initialized
3. A framebuffer `/dev/fb1` is created
4. The screen is ready to use

### Software Activation (BirdNET Display)

The `tft_display.service` is a **separate layer** that:
- Runs **AFTER** hardware initialization
- Connects to the database
- Fetches bird detections
- Displays them on screen

## How Can You Verify?

### 1. Check Hardware Initialization

Verify the TFT screen is recognized by the kernel:

```bash
# Check if framebuffer exists
ls -la /dev/fb1

# Expected result:
# crw-rw---- 1 root video 29, 1 Dec 31 12:34 /dev/fb1
```

```bash
# Check dmesg for TFT initialization
dmesg | grep -i "fb1\|spi\|ili9486\|ads7846"

# Expected result:
# [    3.456789] fbtft: module is from the staging directory
# [    3.567890] fb_ili9486: module is from the staging directory
# [    3.678901] graphics fb1: fb_ili9486 frame buffer device
# [    4.123456] input: ADS7846 Touchscreen as /devices/...
```

### 2. Check Config.txt

```bash
# View TFT configuration
grep -E "spi=on|waveshare|ili9486|ads7846" /boot/firmware/config.txt

# Expected result:
# dtparam=spi=on
# dtoverlay=waveshare35a,speed=16000000,rotate=90
# dtoverlay=ads7846,cs=1,penirq=25,...
```

### 3. Test Framebuffer Directly

You can write directly to the framebuffer (without BirdNET-Pi):

```bash
# Make screen white
sudo cat /dev/zero > /dev/fb1

# Or use fbi to display an image
sudo fbi -T 1 -d /dev/fb1 -noverbose -a your_image.png
```

If this works, then the hardware is correctly initialized by the kernel!

## What If The Screen Doesn't Work?

### Scenario 1: Screen Stays White/Black After Boot

**Diagnosis:**
```bash
# Check if framebuffer exists
ls /dev/fb1

# Check if driver is loaded
lsmod | grep -i "ili9486\|fbtft"

# Check kernel log
dmesg | grep -i "fb1\|ili"
```

**Possible causes:**
1. ❌ `dtoverlay` not correct in config.txt
2. ❌ SPI not enabled
3. ❌ Hardware connection problem

**Solution:**
```bash
# Run installation again
cd ~/BirdNET-Pi
bash scripts/install_tft.sh

# Or configure manually
sudo nano /boot/firmware/config.txt
# Add:
# dtparam=spi=on
# dtoverlay=waveshare35a,speed=16000000,rotate=90

# Reboot
sudo reboot
```

### Scenario 2: Hardware Works, But tft_display.service Doesn't

**Diagnosis:**
```bash
# Check service status
sudo systemctl status tft_display.service

# Check logs
sudo journalctl -u tft_display.service -n 50 --no-pager
```

**Possible causes:**
1. ❌ Python libraries missing (see `TFT_EXIT_CODE_1_FIX.md`)
2. ❌ Database not found
3. ❌ TFT_ENABLED=0 in configuration

**Solution:**
```bash
# Run quick fix
cd ~/BirdNET-Pi
bash scripts/quick_fix_tft.sh
```

## Display Console On TFT (Optional)

If you want to see the **Linux console** on the TFT screen during boot (instead of just birds):

### Step 1: Configure Console

Edit `/boot/firmware/cmdline.txt`:
```bash
sudo nano /boot/firmware/cmdline.txt
```

Add to the end of the line:
```
fbcon=map:10
```

This tells the kernel to send the console to fb1 (the TFT screen).

### Step 2: Reboot

```bash
sudo reboot
```

Now you should see boot messages on the TFT screen!

**Note:** This may conflict with `tft_display.service`. Choose one:
- **Console on TFT**: See boot messages and terminal
- **BirdNET display on TFT**: See bird detections (default)

## Boot Splash Screen (Optional)

You can also add a boot splash screen that appears before BirdNET-Pi starts:

```bash
# Install plymouth
sudo apt-get install plymouth plymouth-themes

# Configure to use fb1
sudo plymouth-set-default-theme -R spinner

# Edit grub/boot config to enable splash
```

However, this is complex and usually not necessary.

## Summary

**Answer to your question:**

✅ **YES**, the TFT screen is ALREADY activated at boot, before BirdNET-Pi starts.

This happens through:
1. **Bootloader** reads `/boot/firmware/config.txt`
2. **Kernel** loads device tree overlays (ILI9486 driver)
3. **Hardware** is initialized, framebuffer `/dev/fb1` created
4. **Then** BirdNET-Pi starts and can use the screen

There is **no additional configuration needed** - the system is already correctly set up by `install_tft.sh`.

If your screen doesn't work:
- It's **NOT** because the hardware isn't activated
- It's likely:
  - Python libraries missing → Use `quick_fix_tft.sh`
  - Hardware connection problem → Check wiring
  - Config.txt not correct → Run `install_tft.sh` again

## Related Documentation

- `TFT_EXIT_CODE_1_FIX.md` - Solving exit code 1 problems
- `TFT_SCREEN_SETUP.md` - Complete setup guide
- `TFT_TESTING_GUIDE.md` - Hardware testing procedures
- `TFT_ARCHITECTURE.md` - Technical architecture details

## Need Help?

If your screen still doesn't work, collect this information:

```bash
# Hardware check
ls -la /dev/fb1
lsmod | grep fbtft

# Kernel log
dmesg | grep -i "fb1\|ili" > ~/tft_dmesg.txt

# Config check
grep -E "spi|overlay" /boot/firmware/config.txt > ~/tft_config.txt

# Service check
sudo systemctl status tft_display.service > ~/tft_service.txt
sudo journalctl -u tft_display.service -n 50 --no-pager > ~/tft_logs.txt
```

Share these files for further assistance.
