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
    
    // Spectrogram configuration
    FFT_SIZE: 2048,
    BACKGROUND_COLOR: 'hsl(280, 100%, 10%)',
    
    // Color mapping for frequency data
    MIN_HUE: 280,
    HUE_RANGE: 120,
  };

  // =================== State Management ===================
  let audioContext = null;
  let analyser = null;
  let sourceNode = null;
  let gainNode = null;
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
      
      // Connect nodes: source -> gain -> analyser -> destination
      sourceNode.connect(gainNode);
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
    // Fill with background color
    ctx.fillStyle = CONFIG.BACKGROUND_COLOR;
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
    
    // Clear canvas
    ctx.fillStyle = CONFIG.BACKGROUND_COLOR;
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
    
    for (let i = 0; i < dataLength; i++) {
      const value = frequencyData[i];
      const normalizedValue = value / 255;
      
      // Calculate color based on frequency intensity
      const hue = Math.round((normalizedValue * CONFIG.HUE_RANGE) + CONFIG.MIN_HUE) % 360;
      const saturation = 100;
      const lightness = 10 + (70 * normalizedValue);
      
      ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
      
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
    // Note: Using the original spectrogram.php endpoint which handles detection data
    // The endpoint is shared between horizontal and vertical spectrogram views
    xhr.open('GET', 'spectrogram.php?ajax_csv=true&newest_file=' + (newestDetectionFile || ''), true);
    
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
    const MAX_LABELS = 10;
    if (currentDetections.length > MAX_LABELS) {
      currentDetections = currentDetections.slice(0, MAX_LABELS);
    }
    
    // Remove old detections (older than 30 seconds)
    const now = Date.now();
    currentDetections = currentDetections.filter(det => 
      (now - det.timestamp) < 30000
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
      const textHeight = 16; // Approximate height
      
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

  // =================== Public API ===================
  
  window.VerticalSpectrogram = {
    initialize,
    stop,
    updateConfig,
    setGain,
    CONFIG
  };

})();
