# Vertical Spectrogram Integration Guide

## Overview
This document describes how to integrate the new vertical scrolling spectrogram feature into a running BirdNET-Pi system.

## What's New
The vertical spectrogram is a new visualization mode that displays audio frequency data with:
- **Vertical scrolling**: Time flows from bottom to top (older audio scrolls upward)
- **Configurable redraw frequency**: Adjustable render interval (default: 100ms for RPi 3)
- **Detection labels**: Real-time bird detection labels with confidence filtering
- **Rotated labels**: Labels are rotated 90° for horizontal readability
- **Performance optimized**: Labels only redraw when new detections arrive or interval elapses

## Files Added
- `/home/runner/work/BirdNET-Pi-MigCount/BirdNET-Pi-MigCount/homepage/static/vertical-spectrogram.js` - Main JavaScript implementation
- `/home/runner/work/BirdNET-Pi-MigCount/BirdNET-Pi-MigCount/scripts/vertical_spectrogram.php` - PHP page for vertical spectrogram view

## Files Modified
- `/home/runner/work/BirdNET-Pi-MigCount/BirdNET-Pi-MigCount/homepage/views.php` - Added navigation menu button and route

## Integration Steps for Running RPi System

### Method 1: Using Git Pull (Recommended)

1. **SSH into your Raspberry Pi**:
   ```bash
   ssh pi@<your-rpi-ip>
   ```

2. **Navigate to BirdNET-Pi directory**:
   ```bash
   cd ~/BirdNET-Pi
   ```

3. **Pull the latest changes**:
   ```bash
   git fetch origin
   git checkout copilot/add-vertical-scroll-spectrogram
   git pull origin copilot/add-vertical-scroll-spectrogram
   ```

4. **Set proper permissions** (if needed):
   ```bash
   chmod 644 homepage/static/vertical-spectrogram.js
   chmod 644 scripts/vertical_spectrogram.php
   chmod 644 homepage/views.php
   ```

5. **Restart web server** (if using Caddy):
   ```bash
   sudo systemctl restart caddy
   ```

6. **Clear browser cache** and navigate to your BirdNET-Pi web interface.

7. **Access the vertical spectrogram**: Click on "Vertical Spectrogram" in the navigation menu.

### Method 2: Manual File Copy

If you prefer to manually copy files:

1. **Copy JavaScript file**:
   ```bash
   scp homepage/static/vertical-spectrogram.js pi@<your-rpi-ip>:~/BirdNET-Pi/homepage/static/
   ```

2. **Copy PHP file**:
   ```bash
   scp scripts/vertical_spectrogram.php pi@<your-rpi-ip>:~/BirdNET-Pi/scripts/
   ```

3. **Update views.php**:
   - Add the menu button in the navigation section
   - Add the include statement for the new view

4. **SSH into RPi and restart services**:
   ```bash
   ssh pi@<your-rpi-ip>
   sudo systemctl restart caddy
   ```

## Configuration Options

The vertical spectrogram includes several configurable parameters that can be adjusted in the web interface:

### Redraw Interval
- **Location**: Slider control labeled "Redraw (ms)"
- **Range**: 50-300ms
- **Default**: 100ms (suitable for RPi 3)
- **Recommendations**:
  - Raspberry Pi 3: 100-150ms
  - Raspberry Pi 5 with HAT: 50-75ms
  - Smartphone/Tablet viewing: 100-150ms
  - Lower values = smoother animation but higher CPU usage

### Minimum Confidence Threshold
- **Location**: Slider control labeled "Min Confidence"
- **Range**: 10-100%
- **Default**: 70%
- **Purpose**: Only displays detection labels for birds detected with confidence >= this threshold

### Additional Controls
- **Gain**: Audio amplification (0-250%)
- **Compression**: Dynamic range compression (toggle)
- **Freq Shift**: Frequency shifting (toggle)
- **RTSP Stream**: Select audio source (if multiple RTSP streams configured)

## Programmatic Configuration

To change default settings, edit the configuration in `homepage/static/vertical-spectrogram.js`:

```javascript
const CONFIG = {
  // Redraw interval in milliseconds
  REDRAW_INTERVAL_MS: 100,        // Change this for different hardware
  
  // Detection label configuration
  DETECTION_CHECK_INTERVAL_MS: 1000,
  MIN_CONFIDENCE_THRESHOLD: 0.7,  // Change this for detection filtering
  
  // Visual settings
  LABEL_FONT: '14px Roboto Flex, sans-serif',
  LABEL_COLOR: 'rgba(255, 255, 255, 0.9)',
  LABEL_BACKGROUND: 'rgba(0, 0, 0, 0.6)',
  
  // FFT settings
  FFT_SIZE: 2048,
};
```

After changing these values, clear browser cache and reload the page.

## Performance Tuning

### For Raspberry Pi 3
- Redraw interval: 100-150ms
- FFT size: 2048 (default)
- Consider disabling some labels if performance is slow

### For Raspberry Pi 5
- Redraw interval: 50-75ms (smoother)
- Can handle more frequent updates

### For Mobile Devices
- Redraw interval: 100-150ms
- Mobile devices typically have sufficient power but battery life is a concern
- The interface is responsive and adapts to screen orientation

## Troubleshooting

### "Loading..." message doesn't disappear
- Check that the audio stream is running: `sudo systemctl status livestream.service`
- Restart the livestream service: `sudo systemctl restart livestream.service`
- Check browser console for JavaScript errors (F12)

### No detection labels appear
- Ensure BirdNET analysis is running: `sudo systemctl status birdnet_analysis.service`
- Check that detection confidence threshold is not too high
- Verify StreamData directory exists and has recent .json files: `ls -lh ~/BirdSongs/StreamData/`

### Performance is slow/choppy
- Increase redraw interval (e.g., from 100ms to 150ms or 200ms)
- Check CPU usage: `top` or `htop`
- Ensure no other CPU-intensive processes are running

### Audio stream not working
- Verify Icecast2 is running: `sudo systemctl status icecast2.service`
- Check audio input device: `arecord -l`
- Review livestream service logs: `sudo journalctl -u livestream.service -n 50`

## Browser Compatibility

Tested and working on:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+ (iOS and macOS)
- Edge 90+

**Note**: The Web Audio API requires a secure context (HTTPS) or localhost. Ensure your BirdNET-Pi is accessed via HTTPS or from localhost.

## Technical Details

### Architecture
- **Canvas-based rendering**: HTML5 canvas for high-performance graphics
- **Web Audio API**: Real-time FFT analysis of audio stream
- **Scrolling mechanism**: Vertical pixel shifting using Canvas `getImageData` and `putImageData`
- **Detection polling**: Regular AJAX polling for new bird detections
- **Label rendering**: Static labels that don't scroll with spectrogram

### Data Flow
1. Audio stream → Web Audio API → FFT Analysis
2. FFT data → Canvas rendering (bottom row)
3. Canvas content scrolls up one pixel per render cycle
4. Detection data polled from backend every 1 second
5. Labels filtered by confidence and rendered on top layer

### Performance Optimizations
- Configurable redraw interval prevents excessive rendering
- Detection labels only update when new data arrives
- Image data buffering for efficient scrolling
- Debounced window resize handling

## Support

For issues or questions:
1. Check the browser console for error messages (F12 → Console)
2. Review systemd service logs: `sudo journalctl -u livestream.service`
3. Open an issue on the GitHub repository with:
   - Raspberry Pi model
   - Browser version
   - Console error messages
   - Screenshots of the problem

## Future Enhancements

Potential improvements for future versions:
- Configurable color schemes
- Zoom controls for frequency range
- Save/load configuration presets
- Export spectrogram as image
- Time markers and frequency labels
- Click-to-identify feature
