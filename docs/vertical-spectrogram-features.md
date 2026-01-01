# Vertical Spectrogram Features

## Overview

The Vertical Spectrogram provides a real-time visualization of audio frequencies with time flowing from bottom to top. This document describes the new features added to enhance mobile/tablet viewing and provide customization options.

## Accessing the Vertical Spectrogram

### From the Main Interface
Navigate to the vertical spectrogram through the BirdNET-Pi web interface:
1. Click **"Vertical Spectrogram"** in the top navigation menu
2. The spectrogram will load in an iframe within the main interface

### Standalone Access (Mobile/Tablet)
For dedicated mobile or tablet viewing, access the spectrogram directly:

**Direct URL:** `http://[your-birdnetpi-address]/scripts/vertical_spectrogram.php`

Example: `http://birdnetpi.local/scripts/vertical_spectrogram.php`

This provides a full-screen, distraction-free view ideal for:
- Mounting on tablets as dedicated displays
- Viewing on smartphones
- Creating bookmarks for quick access
- Using picture-in-picture or split-screen modes

## New Features

### 1. Color Schemes

Choose from four different color palettes to suit your preference or lighting conditions:

#### Purple (Default)
- **Use case:** General purpose, good contrast
- **Colors:** Purple to blue gradient based on frequency intensity
- **Background:** Deep purple

#### Black-White
- **Use case:** High contrast, energy efficient displays, printing
- **Colors:** Grayscale from black (silent) to white (loud)
- **Background:** Black

#### Lava
- **Use case:** Dramatic visualization, heat-map style
- **Colors:** Black → Red → Orange → Yellow → White
- **Background:** Black

#### Green-White
- **Use case:** Night vision friendly, reduced eye strain
- **Colors:** Black → Green → White
- **Background:** Black

**How to change:**
1. Open the Controls panel
2. Select your preferred scheme from the "Color Scheme" dropdown
3. The change takes effect immediately

### 2. Low-Cut Filter

A software-based high-pass filter that removes low-frequency noise (rumble, wind, traffic).

**Features:**
- Enable/disable with checkbox
- Adjustable cutoff frequency: 50-500 Hz
- Default: 200 Hz (removes most environmental noise while preserving bird calls)

**Recommended Settings:**
- **50-100 Hz:** Very light filtering, removes only deep bass
- **150-250 Hz:** Standard filtering for most outdoor environments
- **300-500 Hz:** Aggressive filtering for very noisy environments

**How to use:**
1. Check the "Low-Cut Filter" checkbox to enable
2. Adjust the frequency slider that appears
3. The filter applies in real-time

### 3. Mobile/Tablet Enhancements

#### Fullscreen Mode
- Click the **⛶** button to toggle fullscreen
- Ideal for mounting tablets as dedicated displays
- Press ESC or click the button again to exit

#### Auto-Hide Controls
- Controls automatically fade after 5 seconds of inactivity
- Move mouse/touch screen to show controls again
- Controls become semi-transparent when hidden

#### Collapsible Controls
- Click the **−** button to manually collapse controls
- Click the **+** button to expand
- Useful for maximum viewing area

## Control Panel Reference

### Basic Controls

| Control | Function | Range/Options |
|---------|----------|---------------|
| **RTSP Stream** | Select audio source (if multiple streams) | Stream 1, 2, 3... |
| **Gain** | Audio amplification | 0-250% (default: 100%) |
| **Compression** | Dynamic range compression | On/Off |
| **Freq Shift** | Frequency shifting for ultrasonic | On/Off |
| **Redraw** | Spectrogram update rate | 50-300ms (default: 100ms) |
| **Min Confidence** | Detection label threshold | 10-100% (default: 70%) |

### New Controls

| Control | Function | Range/Options |
|---------|----------|---------------|
| **Color Scheme** | Visual color palette | Purple, Black-White, Lava, Green-White |
| **Low-Cut Filter** | Enable high-pass filter | On/Off |
| **Low-Cut Frequency** | Filter cutoff frequency | 50-500 Hz (default: 200Hz) |
| **Fullscreen** | Toggle fullscreen mode | Button (⛶) |
| **Collapse** | Show/hide controls | Button (−/+) |

## Use Cases

### 1. Dedicated Tablet Display
Mount a tablet showing the vertical spectrogram as a permanent display:
```
http://birdnetpi.local/scripts/vertical_spectrogram.php
```
- Use fullscreen mode
- Enable auto-hide controls
- Choose a color scheme that matches your environment
- Set appropriate gain for your microphone

### 2. Mobile Monitoring
Check bird activity from your smartphone:
- Bookmark the standalone URL
- Use landscape orientation for wider frequency display
- Portrait mode works well for extended time periods
- Reduce redraw interval (150-200ms) to save battery

### 3. Low-Light Viewing
Optimize for viewing in dark conditions:
- Select "Black-White" or "Green-White" color scheme
- Enable browser dark mode
- Collapse controls after setup

### 4. Noisy Environment
Filter out environmental noise:
- Enable Low-Cut Filter
- Set frequency to 200-300 Hz for urban areas
- Adjust gain down if signals are clipping
- Consider higher confidence threshold (80-90%)

## Technical Details

### Color Scheme Implementation
- All color schemes use the same frequency data
- Colors are calculated in real-time based on audio intensity
- Background color changes automatically with scheme
- No performance impact when switching schemes

### Low-Cut Filter
- Implemented using Web Audio API BiquadFilter
- Type: High-pass (Butterworth response)
- Q factor: 0.7071 (optimal flat response)
- No latency added to audio stream
- Filter is in audio chain before visualizer and speakers

### Performance Recommendations

| Device | Redraw Interval | FFT Size |
|--------|----------------|----------|
| Raspberry Pi 3/0W2 | 100-150ms | 2048 |
| Raspberry Pi 4 | 75-100ms | 2048 |
| Raspberry Pi 5 | 50-75ms | 2048 |
| Modern Smartphone | 100-150ms | 2048 |
| Tablet | 75-100ms | 2048 |
| Desktop/Laptop | 50ms | 2048 |

## Troubleshooting

### Controls won't stay visible
- Click the controls area to reset auto-hide timer
- Use the collapse button (−) to manually control visibility
- Move mouse/touch screen periodically

### Colors look washed out
- Try a different color scheme
- Adjust gain control
- Check microphone placement and sensitivity

### Low-cut filter not working
- Ensure checkbox is checked
- Verify frequency slider is visible
- Try increasing cutoff frequency
- Check browser console for errors

### Fullscreen won't activate
- Some browsers require user gesture first
- Try clicking on the page before using fullscreen
- On iOS, use Safari's native fullscreen feature
- Check browser permissions

## Browser Compatibility

**Fully Supported:**
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Mobile:**
- iOS Safari 14+
- Chrome Android 90+
- Firefox Android 88+

**Required APIs:**
- Web Audio API
- Canvas 2D
- Fullscreen API (optional, for fullscreen feature)

## Tips for Best Results

1. **Microphone Placement:** Position away from wind and physical vibrations
2. **Gain Setting:** Start at 100%, adjust based on signal levels
3. **Color Scheme:** Match to ambient lighting (dark schemes for night, bright for day)
4. **Low-Cut Filter:** Enable for outdoor use to remove wind/traffic noise
5. **Confidence Threshold:** Higher values (80-90%) reduce false detections
6. **Redraw Rate:** Lower values (50-75ms) for smoother animation, higher (150-300ms) for slower devices

## Keyboard Shortcuts

When in fullscreen mode:
- **ESC** - Exit fullscreen
- **F11** - Toggle browser fullscreen (desktop)

## Integration with Debian Trixie

The vertical spectrogram is fully compatible with Debian Trixie (Debian 13). All features work as expected on:
- Raspberry Pi OS based on Debian Trixie
- Standard Debian Trixie installations
- x86_64 systems running Debian Trixie

No special configuration is needed for Trixie compatibility.

## Future Enhancements

Possible future additions (not yet implemented):
- Bandwidth selector (focus on specific frequency ranges)
- Recording capability
- Screenshot/export functionality
- Multiple filter types (band-pass, notch)
- Customizable color schemes with user-defined gradients
- Time markers and annotations
