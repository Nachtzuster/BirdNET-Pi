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
 * - Labels don't scroll with spectrogram
 */

(function() {
  'use strict';

  // =================== Configuration ===================
  const CONFIG = {
    // Redraw interval in milliseconds
    // Default: 100ms (suitable for Raspberry Pi 3)
    // For RPi 5 or powerful devices: 50ms
    // For smartphones/tablets: 100-150ms
    REDRAW_INTERVAL_MS: 100,
    
    // Detection label configuration
    DETECTION_CHECK_INTERVAL_MS: 1000,
    MIN_CONFIDENCE_THRESHOLD: 0.7, // Only show detections >= 70% confidence
    LABEL_FONT: '14px Roboto Flex, sans-serif',
    LABEL_COLOR: 'rgba(255, 255, 255, 0.9)',
    LABEL_BACKGROUND: 'rgba(0, 0, 0, 0.6)',
    LABEL_PADDING: 4,
    LABEL_MARGIN: 10, // Margin from canvas edges
    LABEL_BOTTOM_OFFSET: 50, // Distance from bottom for recent detections
    LABEL_HEIGHT: 16, // Approximate text height in pixels
    MAX_VISIBLE_LABELS: 10, // Maximum number of labels to display
    DETECTION_TIMEOUT_MS: 30000, // Remove detections older than 30 seconds
    
    // Spectrogram configuration
    FFT_SIZE: 2048,
    BACKGROUND_COLOR: 'hsl(280, 100%, 10%)',
    
    // Color mapping for frequency data
    MIN_HUE: 280,
    HUE_RANGE: 120,
    
    // Color scheme (default: 'purple', options: 'purple', 'blackwhite', 'lava', 'greenwhite')
    COLOR_SCHEME: 'purple',
    
    // Low-cut filter configuration
    LOW_CUT_ENABLED: false,
    LOW_CUT_FREQUENCY: 200, // Hz - Default cutoff frequency for high-pass filter
  };

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
        if (normalizedValue < 0.33) {
          const r = Math.round((normalizedValue / 0.33) * 255);
          return `rgb(${r}, 0, 0)`;
        } else if (normalizedValue < 0.66) {
          const g = Math.round(((normalizedValue - 0.33) / 0.33) * 200);
          return `rgb(255, ${g}, 0)`;
        } else {
          const intensity = Math.round(((normalizedValue - 0.66) / 0.34) * 255);
          return `rgb(255, ${200 + Math.round(intensity * 0.22)}, ${intensity})`;
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
    
    // Set canvas size
    resizeCanvas();
    
    // Setup audio context
    setupAudioContext();
    
    // Initialize image data for scrolling
    initializeImageData();
    
    // Start rendering loop
    startRenderLoop();
    
    // Start detection check loop
    startDetectionLoop();
    
    // Handle window resize
    window.addEventListener('resize', debounce(handleResize, 250));
    window.addEventListener('orientationchange', debounce(handleResize, 250));
    
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
      analyser.smoothingTimeConstant = 0.8;
      
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
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    // Reinitialize image data after resize
    if (ctx) {
      initializeImageData();
    }
  }

  /**
   * Initialize image data buffer for scrolling
   */
  function initializeImageData() {
    // Fill with background color from current color scheme
    const scheme = COLOR_SCHEMES[CONFIG.COLOR_SCHEME] || COLOR_SCHEMES.purple;
    ctx.fillStyle = scheme.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
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
   * Render a single frame
   */
  function renderFrame() {
    if (!analyser || !frequencyData) return;
    
    // Get frequency data from analyser
    analyser.getByteFrequencyData(frequencyData);
    
    // Scroll existing content up by 1 pixel
    scrollContentUp();
    
    // Draw new FFT row at the bottom
    drawFFTRow();
    
    // Draw detection labels (they don't scroll)
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
   * Process detection data and filter by confidence threshold
   * @param {Array} detections - Array of detection objects
   * @param {number} delay - Delay in seconds
   */
  function processDetections(detections, delay) {
    // Filter detections by confidence threshold
    const validDetections = detections.filter(detection => 
      detection.confidence >= CONFIG.MIN_CONFIDENCE_THRESHOLD
    );
    
    // Calculate position for each detection
    // In vertical mode, we need to map time to vertical position
    // Newer detections are at the bottom
    const newDetections = validDetections.map(detection => {
      return {
        name: detection.common_name,
        confidence: detection.confidence,
        start: detection.start,
        delay: delay,
        // Calculate Y position (bottom is newer)
        // Position near bottom for recent detections using configured offset
        y: canvas.height - CONFIG.LABEL_BOTTOM_OFFSET,
        timestamp: Date.now()
      };
    });
    
    // Add new detections to current list
    currentDetections = [...newDetections, ...currentDetections];
    
    // Limit number of labels to prevent overcrowding
    if (currentDetections.length > CONFIG.MAX_VISIBLE_LABELS) {
      currentDetections = currentDetections.slice(0, CONFIG.MAX_VISIBLE_LABELS);
    }
    
    // Remove old detections (older than configured timeout)
    const now = Date.now();
    currentDetections = currentDetections.filter(det => 
      (now - det.timestamp) < CONFIG.DETECTION_TIMEOUT_MS
    );
  }

  /**
   * Draw detection labels on canvas
   * Labels are rotated 90° and don't scroll with spectrogram
   */
  function drawDetectionLabels() {
    if (currentDetections.length === 0) return;
    
    ctx.save();
    ctx.font = CONFIG.LABEL_FONT;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    
    let yOffset = CONFIG.LABEL_MARGIN;
    
    currentDetections.forEach((detection, index) => {
      // Create label text with confidence
      const labelText = `${detection.name} (${Math.round(detection.confidence * 100)}%)`;
      
      // Measure text
      const textMetrics = ctx.measureText(labelText);
      const textWidth = textMetrics.width;
      const textHeight = CONFIG.LABEL_HEIGHT; // Use configured height
      
      // Position for rotated text (on the right side of canvas)
      const x = canvas.width - CONFIG.LABEL_MARGIN - textHeight;
      const y = yOffset + textWidth / 2;
      
      // Check if label fits on screen
      if (y + textWidth / 2 > canvas.height - CONFIG.LABEL_MARGIN) {
        return; // Skip labels that don't fit
      }
      
      // Draw background
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(-Math.PI / 2); // Rotate 90° counterclockwise
      
      const bgWidth = textWidth + CONFIG.LABEL_PADDING * 2;
      const bgHeight = textHeight + CONFIG.LABEL_PADDING * 2;
      
      ctx.fillStyle = CONFIG.LABEL_BACKGROUND;
      ctx.fillRect(-CONFIG.LABEL_PADDING, -bgHeight / 2, bgWidth, bgHeight);
      
      // Draw text
      ctx.fillStyle = CONFIG.LABEL_COLOR;
      ctx.fillText(labelText, 0, 0);
      
      ctx.restore();
      
      // Update y offset for next label
      yOffset += textWidth + CONFIG.LABEL_PADDING * 2 + 5;
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
    if (filterNode && frequency >= 0 && frequency <= 2000) {
      CONFIG.LOW_CUT_FREQUENCY = frequency;
      if (CONFIG.LOW_CUT_ENABLED) {
        filterNode.frequency.value = frequency;
      }
      console.log('Low-cut frequency set to:', frequency, 'Hz');
    }
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
    CONFIG,
    COLOR_SCHEMES
  };

})();
