/**
 * Vertical Scrolling Live Spectrogram with Detection Labels
 * 
 * Features:
 * - Time flows from bottom to top
 * - Older audio scrolls upward
 * - New FFT rows added at bottom
 * - HTML5 canvas-based rendering
 * - Configurable redraw frequency
 * - Detection labels with confidence threshold filtering
 * - Labels rotated 90° (horizontally readable)
 * - Labels scroll with spectrogram
 */

(function() {
  'use strict';

  // =================== Configuration ===================
  const CONFIG = {
    // Redraw interval in milliseconds
    // Default: 100ms (suitable for Raspberry Pi 3)
    // For RPi 5 or powerful devices: 50ms
    // For smartphones/tablets: 100-150ms
    REDRAW_INTERVAL_MS: 30,
    
    // Detection label configuration
    DETECTION_CHECK_INTERVAL_MS: 1000,
    MIN_CONFIDENCE_THRESHOLD: 0.7, // Only show detections >= 70% confidence
    LABEL_FONT: '13px Roboto Flex, sans-serif',
    LABEL_NAME_COLOR: 'rgba(255, 255, 255, 0.95)',
    LABEL_BACKGROUND: 'rgba(0, 0, 0, 0.75)',
    LABEL_PADDING: 6,
    LABEL_MARGIN: 15, // Margin from canvas edges
    LABEL_BOTTOM_OFFSET: 60, // Distance from bottom for recent detections
    LABEL_HEIGHT: 18, // Approximate text height in pixels
    LABEL_OFFSCREEN_THRESHOLD: 50, // Remove labels this many pixels above canvas top
    MAX_VISIBLE_LABELS: 15, // Maximum number of labels to display
    DETECTION_TIMEOUT_MS: 45000, // Remove detections older than 45 seconds (standard)
    DETECTION_TIMEOUT_LOW_CONFIDENCE_MS: 20000, // 20 seconds for low confidence (faster fade)
    LABEL_ROTATION: -Math.PI / 2, // Default rotation for labels (horizontal)
    
    // Color coding for confidence levels
    CONFIDENCE_HIGH_COLOR: 'rgb(50, 255, 50)', // Bright green for above threshold
    CONFIDENCE_MEDIUM_COLOR: 'rgb(255, 165, 0)', // Orange for near threshold (±5%)
    CONFIDENCE_LOW_COLOR: 'rgba(180, 180, 180, 0.6)', // Light gray for 10% below
    CONFIDENCE_THRESHOLD_RANGE: 0.05, // ±5% range for medium color
    CONFIDENCE_LOW_OFFSET: 0.10, // 10% below threshold for low confidence
    
    // Rapid detection filtering
    RAPID_DETECTION_INTERVAL_MS: 2000, // Don't show detections within 2 seconds of previous high detection
    
    // Spectrogram configuration
    FFT_SIZE: 512,
    BACKGROUND_COLOR: 'hsl(280, 100%, 10%)',
    
    // Color mapping for frequency data
    MIN_HUE: 280,
    HUE_RANGE: 120,
    
    // Color scheme (default: 'purple', options: 'purple', 'blackwhite', 'lava', 'greenwhite')
    COLOR_SCHEME: 'purple',
    
    // Low-cut filter configuration
    LOW_CUT_ENABLED: false,
    LOW_CUT_FREQUENCY: 200, // Hz - Default cutoff frequency for high-pass filter
    LOW_CUT_MIN_FREQUENCY: 50, // Hz - Minimum allowed filter frequency
    LOW_CUT_MAX_FREQUENCY: 1500, // Hz - Maximum allowed filter frequency (UI limit)
    LOW_CUT_ABSOLUTE_MAX: 2000, // Hz - Absolute maximum to prevent invalid values
    
    // Frequency grid configuration
    SHOW_FREQUENCY_GRID: true,
    SAMPLE_RATE: 48000, // Standard audio sample rate
    FREQUENCY_LINES: [1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000], // Hz
    GRID_LINE_COLOR: 'rgba(128, 128, 128, 0.3)', // Medium gray with lower opacity
    GRID_LABEL_COLOR: 'rgba(255, 255, 255, 0.85)', // Brighter white for better visibility
    GRID_LABEL_FONT: '13px Roboto Flex',
    GRID_LABEL_OFFSET_X: 3, // Horizontal offset for grid labels
    GRID_LABEL_OFFSET_Y: 8, // Vertical offset for grid labels
  };
  // --- Frequentiebeperkingen voor syllable-visualisatie ---
  const MIN_FREQ = 1000;    // 1 kHz
  const MAX_FREQ = 11000;   // 11 kHz
  // =================== Color Schemes ===================
  const COLOR_SCHEMES = {
    purple: {
      background: 'hsl(280, 100%, 10%)',
      getColor: function(normalizedValue) {
        const hue = Math.round((normalizedValue * 120) + 280) % 360;
        const saturation = 100;
        const lightness = 10 + (70 * normalizedValue);
        return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
      }
    },
    blackwhite: {
      background: '#000000',
      getColor: function(normalizedValue) {
        const intensity = Math.round(normalizedValue * 255);
        return `rgb(${intensity}, ${intensity}, ${intensity})`;
      }
    },
    lava: {
      background: '#000000',
      getColor: function(normalizedValue) {
        // Lava color scheme: black -> red -> orange -> yellow -> white
        // Color transition thresholds
        const RED_TO_ORANGE_THRESHOLD = 0.33;
        const ORANGE_TO_YELLOW_THRESHOLD = 0.66;
        const REMAINING_RANGE = 0.34; // 1.0 - 0.66
        const YELLOW_BRIGHTNESS_FACTOR = 0.22; // Controls white component in final stage
        
        if (normalizedValue < RED_TO_ORANGE_THRESHOLD) {
          const r = Math.round((normalizedValue / RED_TO_ORANGE_THRESHOLD) * 255);
          return `rgb(${r}, 0, 0)`;
        } else if (normalizedValue < ORANGE_TO_YELLOW_THRESHOLD) {
          const g = Math.round(((normalizedValue - RED_TO_ORANGE_THRESHOLD) / RED_TO_ORANGE_THRESHOLD) * 200);
          return `rgb(255, ${g}, 0)`;
        } else {
          const intensity = Math.round(((normalizedValue - ORANGE_TO_YELLOW_THRESHOLD) / REMAINING_RANGE) * 255);
          return `rgb(255, ${200 + Math.round(intensity * YELLOW_BRIGHTNESS_FACTOR)}, ${intensity})`;
        }
      }
    },
    greenwhite: {
      background: '#000000',
      getColor: function(normalizedValue) {
        // Green to white color scheme
        const green = Math.round(normalizedValue * 255);
        const other = Math.round(normalizedValue * normalizedValue * 255); // Non-linear for better contrast
        return `rgb(${other}, ${green}, ${other})`;
      }
    }
  };

  // =================== State Management ===================
  let audioContext = null;
  let analyser = null;
  let sourceNode = null;
  let gainNode = null;
  let filterNode = null; // High-pass filter for low-cut
  let canvas = null;
  let ctx = null;
  let overlayCanvas = null;
  let overlayCtx = null;
  let audioElement = null;
  
  let imageData = null;
  let frequencyData = null;
  let lastRedrawTime = 0;
  let lastDetectionCheckTime = 0;
  let redrawTimerId = null;
  let detectionCheckTimerId = null;
  let isInitialized = false;
  let newestDetectionFile = null;
  let currentDetections = [];

  // =================== Initialization ===================
  
  /**
   * Initialize the vertical spectrogram
   * @param {HTMLCanvasElement} canvasElement - Canvas element for rendering
   * @param {HTMLAudioElement} audioEl - Audio element for the stream
   */
  function initialize(canvasElement, audioEl) {
    if (isInitialized) {
      console.warn('Vertical spectrogram already initialized');
      return;
    }

    canvas = canvasElement;
    audioElement = audioEl;
    ctx = canvas.getContext('2d');
    
    // Get overlay canvas for frequency labels
    overlayCanvas = document.getElementById('frequency-labels-overlay');
    if (overlayCanvas) {
      overlayCtx = overlayCanvas.getContext('2d');
    }
    
    // Set canvas size
    resizeCanvas();
    
    // Setup audio context
    setupAudioContext();
    
    // Initialize image data for scrolling
    initializeImageData();
    
    // Draw initial frequency labels on overlay
    drawFrequencyLabels();
    
    // Start rendering loop
    startRenderLoop();
    
    // Start detection check loop
    startDetectionLoop();
    
    // Handle window resize
    window.addEventListener('resize', debounce(handleResize, 250));
    window.addEventListener('orientationchange', debounce(handleResize, 250));
    
    // Add click handler for screenshots
    canvas.addEventListener('click', captureScreenshot);
    canvas.style.cursor = 'pointer';
    
    isInitialized = true;
    console.log('Vertical spectrogram initialized');
  }

  /**
   * Setup Audio Context and Web Audio API nodes
   */
  function setupAudioContext() {
    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = CONFIG.FFT_SIZE;
      analyser.smoothingTimeConstant = 0.0;
      
      // Create source from audio element
      sourceNode = audioContext.createMediaElementSource(audioElement);
      
      // Create gain node
      gainNode = audioContext.createGain();
      gainNode.gain.value = 1;
      
      // Create high-pass filter (low-cut filter)
      filterNode = audioContext.createBiquadFilter();
      filterNode.type = 'highpass';
      filterNode.frequency.value = CONFIG.LOW_CUT_FREQUENCY;
      filterNode.Q.value = 0.7071; // Butterworth response
      
      // Connect nodes: source -> filter -> gain -> analyser -> destination
      // Filter is always in the chain but can be bypassed by setting frequency to 0
      sourceNode.connect(filterNode);
      filterNode.connect(gainNode);
      gainNode.connect(analyser);
      gainNode.connect(audioContext.destination);
      
      // Initialize frequency data array
      frequencyData = new Uint8Array(analyser.frequencyBinCount);
      
      console.log('Audio context setup complete');
    } catch (error) {
      console.error('Failed to setup audio context:', error);
      throw error;
    }
  }

  /**
   * Resize canvas to match window size
   */
  function resizeCanvas() {
    // Get the canvas container dimensions
    const container = canvas.parentElement;
    if (!container) {
      throw new Error('Canvas has no parent element - cannot resize');
    }
    
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    
    // Resize overlay canvas to match
    if (overlayCanvas) {
      overlayCanvas.width = container.clientWidth;
      overlayCanvas.height = container.clientHeight;
    }
    
    // Reinitialize image data after resize
    if (ctx) {
      initializeImageData();
    }
    
    // Redraw frequency labels on overlay
    drawFrequencyLabels();
  }

  /**
   * Initialize image data buffer for scrolling
   */
  function initializeImageData() {
    // Fill with background color from current color scheme
    const scheme = COLOR_SCHEMES[CONFIG.COLOR_SCHEME] || COLOR_SCHEMES.purple;
    ctx.fillStyle = scheme.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Set better text rendering
    ctx.imageSmoothingEnabled = false;
    ctx.imageSmoothingQuality = 'high';
    
    // Create image data buffer
    imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  }

  /**
   * Handle window resize
   */
  function handleResize() {
    resizeCanvas();
    // Clear detections on resize
    currentDetections = [];
  }

  // =================== Rendering Loop ===================

  /**
   * Start the render loop with configurable interval
   */
  function startRenderLoop() {
    const render = () => {
      const now = performance.now();
      
      // Only render if enough time has passed
      if (now - lastRedrawTime >= CONFIG.REDRAW_INTERVAL_MS) {
        renderFrame();
        lastRedrawTime = now;
      }
      
      // Schedule next render
      redrawTimerId = requestAnimationFrame(render);
    };
    
    render();
  }

  /**
   * Draw frequency grid lines on the canvas
   * In vertical mode, frequency lines are vertical (time flows vertically)
   */
  function drawFrequencyGrid() {
    if (!CONFIG.SHOW_FREQUENCY_GRID) return;
    
    ctx.save();
    ctx.strokeStyle = CONFIG.GRID_LINE_COLOR;
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    
    const nyquist = CONFIG.SAMPLE_RATE / 2;
    const dataLength = frequencyData.length;
    const barWidth = canvas.width / dataLength;
    
    CONFIG.FREQUENCY_LINES.forEach(freq => {
      if (freq <= nyquist) {
        // Calculate X position for this frequency
        const binIndex = (freq / nyquist) * dataLength;
        const x = binIndex * barWidth;
        
        // Draw vertical line only (labels are on overlay)
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
      }
    });
    
    ctx.restore();
  }

  /**
   * Draw frequency labels on the fixed overlay canvas
   * These labels don't scroll with the spectrogram
   */
  function drawFrequencyLabels() {
    if (!CONFIG.SHOW_FREQUENCY_GRID || !overlayCtx || !overlayCanvas) return;
    
    // Clear overlay
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    
    overlayCtx.save();
    overlayCtx.fillStyle = CONFIG.GRID_LABEL_COLOR;
    overlayCtx.font = CONFIG.GRID_LABEL_FONT;
    overlayCtx.textAlign = 'left';
    overlayCtx.textBaseline = 'top';
    
    const nyquist = CONFIG.SAMPLE_RATE / 2;
    // Safely get data length
    const dataLength = frequencyData ? frequencyData.length : (analyser ? analyser.frequencyBinCount : 1024);
    const barWidth = overlayCanvas.width / dataLength;
    
    CONFIG.FREQUENCY_LINES.forEach(freq => {
      if (freq <= nyquist) {
        // Calculate X position for this frequency
        const binIndex = (freq / nyquist) * dataLength;
        const x = binIndex * barWidth;
        
        // Draw frequency label at top
        overlayCtx.save();
        overlayCtx.translate(x + CONFIG.GRID_LABEL_OFFSET_X, CONFIG.GRID_LABEL_OFFSET_Y);
        overlayCtx.rotate(-Math.PI / 2);
        overlayCtx.fillText(freq >= 1000 ? (freq/1000) + 'kHz' : freq + 'Hz', 0, 0);
        overlayCtx.restore();
      }
    });
    
    overlayCtx.restore();
  }

  /**
   * Render a single frame
   */
  function renderFrame() {
  if (!analyser || !frequencyData) return;

  // Haal ruwe FFT bins op (0–255)
  analyser.getByteFrequencyData(frequencyData);

  // Converteer lineaire magnitude → pseudo-dB in-place
  // Dit verhoogt zichtbaarheid van zachte syllables
  for (let i = 0; i < frequencyData.length; i++) {
    const v = frequencyData[i] / 255.0;          // 0.0 – 1.0
    let db = 20 * Math.log10(v + 1e-6);           // log schaal
    db = Math.max(db, -80);                       // noise floor
    frequencyData[i] = Math.floor(
      ((db + 80) / 80) * 255                      // normaliseer naar 0–255
    );
  }

  // Scroll bestaande inhoud exact 1 pixel omhoog
  scrollContentUp();

  // Teken nieuwe FFT-rij onderaan (1 tijdstap)
  drawFFTRow();

  // Grid enkel opnieuw tekenen indien nodig
  // (optioneel optimaliseerbaar, maar correct zo)
  drawFrequencyGrid();

  // Detectielabels volgen de spectrogram-scroll
  drawDetectionLabels();
}
  /**
   * Scroll canvas content up by 1 pixel
   */
  function scrollContentUp() {
    // Get current image data (excluding bottom row)
    const currentImage = ctx.getImageData(0, 1, canvas.width, canvas.height - 1);
    
    // Clear canvas with current color scheme background
    const scheme = COLOR_SCHEMES[CONFIG.COLOR_SCHEME] || COLOR_SCHEMES.purple;
    ctx.fillStyle = scheme.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw shifted image (moved up by 1 pixel)
    ctx.putImageData(currentImage, 0, 0);
    
    // Scroll detection labels up by 1 pixel
    currentDetections.forEach(detection => {
      if (typeof detection.y === 'number') {
        detection.y -= 1;
      }
    });
    
    // Remove detections that have scrolled off the top of the canvas
    currentDetections = currentDetections.filter(det => det.y > -CONFIG.LABEL_OFFSCREEN_THRESHOLD);
  }

  /**
   * Draw new FFT row at the bottom of the canvas
   */
  function drawFFTRow() {
    const dataLength = frequencyData.length;
    const barWidth = canvas.width / dataLength;
    const y = canvas.height - 1; // Bottom row
    
    // Get current color scheme
    const scheme = COLOR_SCHEMES[CONFIG.COLOR_SCHEME] || COLOR_SCHEMES.purple;
    
    for (let i = 0; i < dataLength; i++) {
      const value = frequencyData[i];
      const normalizedValue = value / 255;
      
      // Get color from current scheme
      ctx.fillStyle = scheme.getColor(normalizedValue);
      
      const x = i * barWidth;
      ctx.fillRect(x, y, Math.ceil(barWidth), 1);
    }
  }

  // =================== Detection Labels ===================

  /**
   * Start the detection check loop
   */
  function startDetectionLoop() {
    const checkDetections = () => {
      const now = performance.now();
      
      // Only check if enough time has passed
      if (now - lastDetectionCheckTime >= CONFIG.DETECTION_CHECK_INTERVAL_MS) {
        fetchDetections();
        lastDetectionCheckTime = now;
      }
      
      // Schedule next check
      detectionCheckTimerId = setTimeout(checkDetections, CONFIG.DETECTION_CHECK_INTERVAL_MS);
    };
    
    checkDetections();
  }

  /**
   * Fetch detection data from backend
   */
  function fetchDetections() {
    const xhr = new XMLHttpRequest();
    // Call the detection endpoint on the current page (vertical_spectrogram.php)
    // The AJAX handling code is included in vertical_spectrogram.php
    // Use a relative path that works from the views.php iframe context
    const endpoint = window.location.pathname.includes('vertical_spectrogram') 
      ? 'vertical_spectrogram.php?ajax_csv=true&newest_file=' + encodeURIComponent(newestDetectionFile || '')
      : '../scripts/vertical_spectrogram.php?ajax_csv=true&newest_file=' + encodeURIComponent(newestDetectionFile || '');
    xhr.open('GET', endpoint, true);
    
    xhr.onload = function() {
      if (xhr.status === 200 && xhr.responseText.length > 0 && !xhr.responseText.includes('Database')) {
        try {
          const response = JSON.parse(xhr.responseText);
          
          // Update newest file tracker
          if (response.file_name) {
            newestDetectionFile = response.file_name;
          }
          
          // Process detections
          if (response.detections && Array.isArray(response.detections)) {
            processDetections(response.detections, response.delay || 0);
          }
        } catch (error) {
          console.error('Error parsing detection data:', error);
        }
      }
    };
    
    xhr.onerror = function() {
      console.error('Failed to fetch detection data');
    };
    
    xhr.send();
  }

  /**
   * Get color for confidence level based on threshold
   * @param {number} confidence - Detection confidence (0-1)
   * @returns {string} CSS color string
   */
  function getConfidenceColor(confidence) {
    const threshold = CONFIG.MIN_CONFIDENCE_THRESHOLD;
    const diff = confidence - threshold;
    
    if (diff >= 0) {
      // Above or at threshold - bright green
      return CONFIG.CONFIDENCE_HIGH_COLOR;
    } else if (Math.abs(diff) <= CONFIG.CONFIDENCE_THRESHOLD_RANGE) {
      // Within ±5% of threshold - orange
      return CONFIG.CONFIDENCE_MEDIUM_COLOR;
    } else if (Math.abs(diff) <= CONFIG.CONFIDENCE_LOW_OFFSET) {
      // Within 10% below threshold - light gray
      return CONFIG.CONFIDENCE_LOW_COLOR;
    } else {
      // More than 10% below threshold - don't show
      return null;
    }
  }

  /**
   * Process detection data and filter by confidence threshold
   * @param {Array} detections - Array of detection objects
   * @param {number} delay - Delay in seconds
   */
  function processDetections(detections, delay) {
    const now = Date.now();
    
    // Filter detections based on confidence and color coding
    const validDetections = detections.filter(detection => {
      const color = getConfidenceColor(detection.confidence);
      // Only show if we have a color (within acceptable range)
      return color !== null;
    });
    
    // Group detections by timestamp to identify multi-detections
    const detectionGroups = {};
    validDetections.forEach(detection => {
      const key = Math.floor(detection.start * 10); // Group by 0.1s intervals
      if (!detectionGroups[key]) {
        detectionGroups[key] = [];
      }
      detectionGroups[key].push(detection);
    });
    
    // Check for rapid consecutive detections (within RAPID_DETECTION_INTERVAL_MS)
    // Only filter out if it's a single species, not multi-detections
    const recentHighConfidence = currentDetections.filter(det => 
      det.confidence >= CONFIG.MIN_CONFIDENCE_THRESHOLD && 
      (now - det.timestamp) < CONFIG.RAPID_DETECTION_INTERVAL_MS
    );
    
    const newDetections = [];
    Object.values(detectionGroups).forEach(group => {
      // Multi-detections (multiple species in same clip) - always show
      const isMultiDetection = group.length > 1;
      
      if (isMultiDetection) {
        // Show all species in multi-detection
        group.forEach(detection => {
          newDetections.push({
            name: detection.common_name,
            confidence: detection.confidence,
            start: detection.start,
            delay: delay,
            y: canvas.height - CONFIG.LABEL_BOTTOM_OFFSET,
            timestamp: now,
            isMulti: true
          });
        });
      } else {
        // Single detection - check for rapid consecutive
        const detection = group[0];
        const isDuplicate = recentHighConfidence.some(recent => 
          recent.name === detection.common_name &&
          Math.abs(recent.start - detection.start) < 2.0 // Within 2 seconds
        );
        
        if (!isDuplicate) {
          newDetections.push({
            name: detection.common_name,
            confidence: detection.confidence,
            start: detection.start,
            delay: delay,
            y: canvas.height - CONFIG.LABEL_BOTTOM_OFFSET,
            timestamp: now,
            isMulti: false
          });
        }
      }
    });
    
    // Add new detections to current list
    currentDetections = [...newDetections, ...currentDetections];
    
    // Limit number of labels to prevent overcrowding
    if (currentDetections.length > CONFIG.MAX_VISIBLE_LABELS) {
      currentDetections = currentDetections.slice(0, CONFIG.MAX_VISIBLE_LABELS);
    }
    
    // Remove old detections based on confidence level (low confidence fades faster)
    currentDetections = currentDetections.filter(det => {
      const age = now - det.timestamp;
      const color = getConfidenceColor(det.confidence);
      
      // If color is null, remove immediately
      if (color === null) return false;
      
      // Low confidence detections (gray) fade faster
      if (color === CONFIG.CONFIDENCE_LOW_COLOR) {
        return age < CONFIG.DETECTION_TIMEOUT_LOW_CONFIDENCE_MS;
      }
      
      // Others use standard timeout
      return age < CONFIG.DETECTION_TIMEOUT_MS;
    });
  }

  /**
   * Draw detection labels on canvas
   * Labels are displayed on the spectrogram and scroll upward with the content
   * In vertical mode, labels are rotated 90 degrees to be horizontally readable
   */
  function drawDetectionLabels() {
    if (currentDetections.length === 0) return;
    
    ctx.save();
    ctx.font = CONFIG.LABEL_FONT;
    
    currentDetections.forEach((detection, index) => {
      // Get confidence color
      const confidenceColor = getConfidenceColor(detection.confidence);
      if (!confidenceColor) return; // Skip if no valid color
      
      const confidencePercent = Math.round(detection.confidence * 100);
      const confidenceText = `+${confidencePercent}%`;
      
      // Create label text parts
      const nameText = detection.name;
      
      // Measure text parts
      const nameMetrics = ctx.measureText(nameText);
      const confidenceMetrics = ctx.measureText(confidenceText);
      const spaceMetrics = ctx.measureText(' ');
      
      const totalWidth = nameMetrics.width + spaceMetrics.width + confidenceMetrics.width;
      const textHeight = CONFIG.LABEL_HEIGHT;
      
      // Position labels on the right side of canvas at their current Y position
      // X position is on the right side with some margin
      const x = canvas.width - CONFIG.LABEL_MARGIN;
      const y = detection.y;
      
      // Skip labels that are off screen
      if (y < -textHeight || y > canvas.height + textHeight) {
        return;
      }
      
      // Save context for rotation
      ctx.save();
      
      // Move to label position and rotate 90 degrees counterclockwise for correct orientation
      ctx.translate(x, y);
      ctx.rotate(CONFIG.LABEL_ROTATION); // Rotate by configured amount
      
      // Now draw text normally - it will appear horizontally in the vertical spectrogram
      // Use right-align so text is aligned against the right edge of the canvas
      ctx.textAlign = 'right';
      // Use top baseline so text extends downward in rotated coords (upward in final view)
      ctx.textBaseline = 'top';
      
      // Draw background rectangle
      // In rotated coordinate system: right-align means rectangle extends to the left (upward in final view)
      const bgWidth = totalWidth + CONFIG.LABEL_PADDING * 2;
      const bgHeight = textHeight + CONFIG.LABEL_PADDING * 2;
      
      ctx.fillStyle = CONFIG.LABEL_BACKGROUND;
      ctx.fillRect(-bgWidth + CONFIG.LABEL_PADDING, -CONFIG.LABEL_PADDING, bgWidth, bgHeight);
      
      // Draw confidence in color-coded style
      // In rotated coordinates: positioned at right edge (appears at bottom in final view)
      ctx.fillStyle = confidenceColor;
      ctx.fillText(confidenceText, -CONFIG.LABEL_PADDING, 0);
      
      // Draw species name in white
      // In rotated coordinates: positioned left of confidence (appears above in final view)
      ctx.fillStyle = CONFIG.LABEL_NAME_COLOR;
      const nameX = -CONFIG.LABEL_PADDING - confidenceMetrics.width - spaceMetrics.width;
      ctx.fillText(nameText, nameX, 0);
      
      // Restore context after rotation
      ctx.restore();
    });
    
    ctx.restore();
  }

  // =================== Utility Functions ===================

  /**
   * Debounce function to limit function calls
   * @param {Function} func - Function to debounce
   * @param {number} wait - Wait time in milliseconds
   * @returns {Function} Debounced function
   */
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  /**
   * Capture screenshot of canvas and save it
   */
  function captureScreenshot() {
    if (!canvas) {
      console.error('Canvas not available for screenshot');
      return;
    }
    
    try {
      // Create timestamp for filename
      const now = new Date();
      const timestamp = now.getFullYear() + '-' + 
                       String(now.getMonth() + 1).padStart(2, '0') + '-' +
                       String(now.getDate()).padStart(2, '0') + '_' +
                       String(now.getHours()).padStart(2, '0') + '-' +
                       String(now.getMinutes()).padStart(2, '0') + '-' +
                       String(now.getSeconds()).padStart(2, '0');
      
      // Convert canvas to blob
      canvas.toBlob(function(blob) {
        if (!blob) {
          console.error('Failed to create image blob');
          return;
        }
        
        // Create FormData to send to server
        const formData = new FormData();
        formData.append('screenshot', blob, 'spectrogram_' + timestamp + '.png');
        formData.append('timestamp', timestamp);
        
        // Send to server
        const xhr = new XMLHttpRequest();
        // Use relative path that works from current context
        const endpoint = window.location.pathname.includes('vertical_spectrogram')
          ? window.location.pathname + '?save_screenshot=true'
          : '../scripts/vertical_spectrogram.php?save_screenshot=true';
        xhr.open('POST', endpoint, true);
        
        xhr.onload = function() {
          if (xhr.status === 200) {
            console.log('Screenshot saved successfully');
            // Visual feedback
            showScreenshotFeedback();
          } else {
            console.error('Failed to save screenshot:', xhr.status, xhr.responseText);
          }
        };
        
        xhr.onerror = function() {
          console.error('Error sending screenshot to server');
        };
        
        xhr.send(formData);
      }, 'image/png');
      
    } catch (error) {
      console.error('Error capturing screenshot:', error);
    }
  }
  
  /**
   * Show visual feedback when screenshot is taken
   */
  function showScreenshotFeedback() {
    // Flash effect on canvas
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.backgroundColor = 'white';
    overlay.style.opacity = '0.7';
    overlay.style.pointerEvents = 'none';
    overlay.style.zIndex = '9999';
    overlay.style.transition = 'opacity 0.3s';
    
    document.body.appendChild(overlay);
    
    // Fade out after brief flash
    setTimeout(() => {
      overlay.style.opacity = '0';
      setTimeout(() => {
        document.body.removeChild(overlay);
      }, 300);
    }, 100);
  }

  /**
   * Stop the spectrogram
   */
  function stop() {
    if (redrawTimerId) {
      cancelAnimationFrame(redrawTimerId);
      redrawTimerId = null;
    }
    
    if (detectionCheckTimerId) {
      clearTimeout(detectionCheckTimerId);
      detectionCheckTimerId = null;
    }
    
    isInitialized = false;
    console.log('Vertical spectrogram stopped');
  }

  /**
   * Update configuration
   * @param {Object} newConfig - New configuration values
   */
  function updateConfig(newConfig) {
    Object.assign(CONFIG, newConfig);
    
    // If any frequency grid-related config changed, redraw labels
    const gridRelatedKeys = ['SHOW_FREQUENCY_GRID', 'GRID_LABEL_COLOR', 'GRID_LABEL_FONT', 
                              'FREQUENCY_LINES', 'GRID_LABEL_OFFSET_X', 'GRID_LABEL_OFFSET_Y'];
    const shouldRedrawLabels = gridRelatedKeys.some(key => key in newConfig);
    
    if (shouldRedrawLabels) {
      drawFrequencyLabels();
    }
    
    console.log('Configuration updated:', CONFIG);
  }

  /**
   * Set gain value
   * @param {number} value - Gain value (0-2)
   */
  function setGain(value) {
    if (gainNode) {
      gainNode.gain.value = value;
    }
  }

  /**
   * Set color scheme
   * @param {string} schemeName - Color scheme name ('purple', 'blackwhite', 'lava', 'greenwhite')
   */
  function setColorScheme(schemeName) {
    if (COLOR_SCHEMES[schemeName]) {
      CONFIG.COLOR_SCHEME = schemeName;
      // Reinitialize background with new color scheme
      initializeImageData();
      console.log('Color scheme changed to:', schemeName);
    } else {
      console.error('Unknown color scheme:', schemeName);
    }
  }

  /**
   * Enable or disable low-cut filter
   * @param {boolean} enabled - Whether to enable the filter
   */
  function setLowCutFilter(enabled) {
    if (filterNode) {
      CONFIG.LOW_CUT_ENABLED = enabled;
      // When disabled, set frequency very low (effectively bypassing)
      // When enabled, use configured frequency
      filterNode.frequency.value = enabled ? CONFIG.LOW_CUT_FREQUENCY : 1;
      console.log('Low-cut filter', enabled ? 'enabled' : 'disabled');
    }
  }

  /**
   * Set low-cut filter frequency
   * @param {number} frequency - Cutoff frequency in Hz
   */
  function setLowCutFrequency(frequency) {
    if (filterNode && frequency >= 0 && frequency <= CONFIG.LOW_CUT_ABSOLUTE_MAX) {
      CONFIG.LOW_CUT_FREQUENCY = frequency;
      if (CONFIG.LOW_CUT_ENABLED) {
        filterNode.frequency.value = frequency;
      }
      console.log('Low-cut frequency set to:', frequency, 'Hz');
    }
  }

  /**
   * Set rotation for detection labels
   * @param {number} rotationRadians - Rotation in radians
   */
  function normalizeRotation(rotationRadians) {
    const FULL_TURN = Math.PI * 2;
    let normalized = ((rotationRadians % FULL_TURN) + FULL_TURN) % FULL_TURN;
    if (normalized > Math.PI) {
      normalized -= FULL_TURN;
    }
    return normalized;
  }

  function setLabelRotation(rotationRadians) {
    if (!Number.isFinite(rotationRadians)) {
      console.warn('Invalid label rotation value:', rotationRadians);
      return;
    }
    CONFIG.LABEL_ROTATION = normalizeRotation(rotationRadians);
  }

  // =================== Public API ===================
  
  window.VerticalSpectrogram = {
    initialize,
    stop,
    updateConfig,
    setGain,
    setColorScheme,
    setLowCutFilter,
    setLowCutFrequency,
    setLabelRotation,
    captureScreenshot,
    CONFIG,
    COLOR_SCHEMES
  };

})();
