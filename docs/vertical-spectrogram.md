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
- **Display Settings**: Control redraw interval, color scheme, and frequency grid visibility
- **Detection Filters**: Set minimum confidence threshold for displayed detections
- **Frequency Filter**: Enable/disable low-cut filter with adjustable cutoff frequency

### Mobile Optimizations
- Responsive layout that adapts to mobile screens
- Sidebar moves to bottom on mobile devices for better accessibility
- Touch-friendly controls
- Optimized canvas size for mobile viewing

### Detection Labels

#### Vertical Spectrogram
Species detections are displayed on the left side of the spectrogram with:
- Species common name
- Confidence percentage
- Only shows detections above the configured confidence threshold (default 70%)
- Automatically removes old detections after 45 seconds
- Maximum of 15 labels shown at once

#### Normal (Horizontal) Spectrogram
Species detections are displayed as rotated labels (90° counter-clockwise) positioned at the bottom of the canvas:
- Labels appear at the detection time position
- Rotated for better readability and space efficiency
- Shows species name with confidence-based opacity
- Positioned at the baseline of detections

### Frequency Grid Lines

Both spectrograms now include optional frequency reference lines:

#### Frequencies Displayed
- 1 kHz, 2 kHz, 3 kHz, 4 kHz, 5 kHz
- 6 kHz, 8 kHz, 10 kHz, 12 kHz

#### In Vertical Spectrogram
- Vertical lines (since time flows vertically)
- Toggle on/off via "Show Frequency Grid" checkbox
- Labels rotated 90° at top of canvas
- Helps identify frequency ranges of bird calls

#### In Normal Spectrogram
- Horizontal lines (traditional orientation)
- Always displayed
- Labels on left side
- Standard frequency reference for analysis

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
- Standard-compliant CSS properties for cross-browser support

### Detection Data
Detections are fetched every second from the BirdNET-Pi analysis system and filtered based on:
- Minimum confidence threshold (configurable via slider)
- Recency (only shows detections from the last 45 seconds)

### Frequency Grid
- Based on 48kHz sample rate (standard for audio)
- Nyquist frequency: 24kHz (maximum representable frequency)
- Grid lines calculated from FFT bin positions
- Helps identify bird call frequency ranges for species identification

## Troubleshooting

If you experience issues:
1. Ensure your BirdNET-Pi is running and accessible
2. Check that the audio stream is active
3. Verify that analysis is enabled in BirdNET-Pi settings
4. Try refreshing the page
5. On mobile, ensure you're not in low-power mode which may affect performance
6. If frequency lines don't appear, check that JavaScript is enabled

## Browser Compatibility
The vertical spectrogram works best on:
- Chrome/Chromium (desktop and mobile)
- Safari (iOS/macOS)
- Firefox (desktop and mobile)
- Edge (desktop)

Older browsers may have reduced functionality.

## Field Usage Tips

### For Bird Watching
- Use frequency grid to identify characteristic frequency ranges
- Different species have distinct frequency patterns
- Lower frequencies (1-3 kHz): Larger birds, owls
- Mid frequencies (3-6 kHz): Common songbirds
- High frequencies (6-12 kHz): Small birds, warblers

### Mobile Best Practices
- Access via direct link for fullscreen experience
- Use landscape orientation on tablets for better view
- Adjust confidence threshold to filter noise
- Enable frequency grid for reference during field observation
