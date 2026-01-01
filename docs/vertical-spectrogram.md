# Vertical Spectrogram Access Guide

## Desktop Access
To access the vertical spectrogram on desktop:
1. Open BirdNET-Pi in your browser
2. Click "Vertical Spectrogram" in the top navigation bar

## Mobile/Tablet Direct Access

### Option 1: Direct Link
Access the vertical spectrogram directly by navigating to:
```
http://[your-birdnetpi-address]/vertical_spectrogram.html
```
or
```
http://[your-birdnetpi-address]/scripts/vertical_spectrogram.php
```

Replace `[your-birdnetpi-address]` with your BirdNET-Pi address (e.g., `birdnetpi.local` or your Pi's IP address).

### Option 2: Through Main Interface
1. Open BirdNET-Pi in your mobile browser
2. Click the menu icon (☰) in the top navigation
3. Select "Vertical Spectrogram"

## Features

### Sidebar Controls
The vertical spectrogram now has a dedicated sidebar with organized control groups:

- **Stream Selection**: Choose between RTSP streams (if configured)
- **Audio Settings**: Adjust gain, compression, and frequency shift
- **Display Settings**: Control redraw interval and color scheme
- **Detection Filters**: Set minimum confidence threshold for displayed detections
- **Frequency Filter**: Enable/disable low-cut filter with adjustable cutoff frequency

### Mobile Optimizations
- Responsive layout that adapts to mobile screens
- Sidebar moves to bottom on mobile devices for better accessibility
- Touch-friendly controls
- Optimized canvas size for mobile viewing

### Detection Labels
Species detections are displayed on the left side of the spectrogram with:
- Species common name
- Confidence percentage
- Only shows detections above the configured confidence threshold (default 70%)
- Automatically removes old detections after 45 seconds
- Maximum of 15 labels shown at once

### Color Schemes
Choose from multiple color schemes:
- **Purple** (default): Traditional spectrogram appearance
- **Black-White**: High contrast monochrome
- **Lava**: Warm colors from black to red to yellow
- **Green-White**: Cool colors for a different aesthetic

## Technical Details

### Canvas Width
The spectrogram canvas is now limited to a maximum width of 600px for better viewing on various devices while leaving room for the sidebar controls.

### Rendering Quality
- Improved anti-aliasing for sharper text
- Better image smoothing for cleaner graphics
- Crisp edge rendering for the spectrogram data

### Detection Data
Detections are fetched every second from the BirdNET-Pi analysis system and filtered based on:
- Minimum confidence threshold (configurable via slider)
- Recency (only shows detections from the last 45 seconds)

## Troubleshooting

If you experience issues:
1. Ensure your BirdNET-Pi is running and accessible
2. Check that the audio stream is active
3. Verify that analysis is enabled in BirdNET-Pi settings
4. Try refreshing the page
5. On mobile, ensure you're not in low-power mode which may affect performance

## Browser Compatibility
The vertical spectrogram works best on:
- Chrome/Chromium (desktop and mobile)
- Safari (iOS/macOS)
- Firefox (desktop and mobile)
- Edge (desktop)

Older browsers may have reduced functionality.
