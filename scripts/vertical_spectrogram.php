<?php
error_reporting(E_ERROR);
ini_set('display_errors',1);

require_once __DIR__ . '/common.php';
$home = get_home();
$config = get_config();

if(!empty($config['FREQSHIFT_RECONNECT_DELAY']) && is_numeric($config['FREQSHIFT_RECONNECT_DELAY'])){
    $FREQSHIFT_RECONNECT_DELAY = ($config['FREQSHIFT_RECONNECT_DELAY']);
}else{
    $FREQSHIFT_RECONNECT_DELAY = 4000;
}

// Configuration constants
define('DEFAULT_FREQSHIFT_RECONNECT_DELAY', 4000);
define('RTSP_STREAM_RECONNECT_DELAY', 10000);

// Handle AJAX request for detection data (reuse existing endpoint logic)
if(isset($_GET['ajax_csv'])) {
  $RECS_DIR = $config["RECS_DIR"];
  $STREAM_DATA_DIR = $RECS_DIR . "/StreamData/";

  if (empty($config['RTSP_STREAM'])) {
    $look_in_directory = $STREAM_DATA_DIR;
    $files = scandir($look_in_directory, SCANDIR_SORT_ASCENDING);
    //Extract the filename, positions 0 and 1 are the folder hierarchy '.' and '..'
    $newest_file = isset($files[2]) ? $files[2] : null;
    if ($newest_file === null) {
      die(); // No files available
    }
  }
  else {
    $look_in_directory = $STREAM_DATA_DIR;

    //Load the file in the directory
    $files = scandir($look_in_directory, SCANDIR_SORT_ASCENDING);

    //Because there might be more than 1 stream, we can't really assume the file at index 2 is the latest, or even for the stream being listened to
    //Read the RTSP_STREAM_TO_LIVESTREAM setting, then try to find that CSV file
    if(!empty($config['RTSP_STREAM_TO_LIVESTREAM']) && is_numeric($config['RTSP_STREAM_TO_LIVESTREAM'])){
        //The stored setting of RTSP_STREAM_TO_LIVESTREAM is 0 based, but filenames are 1's based, so just add 1 to the config value
        //so we can match up the stream the user is listening to with the appropriate filename
        $RTSP_STREAM_LISTENED_TO = ($config['RTSP_STREAM_TO_LIVESTREAM'] + 1);
    }else{
        //Setting is invalid somehow
        //The stored setting of RTSP_STREAM_TO_LIVESTREAM is 0 based, but filenames are 1's based, so just add 1 to the config value
        //This will be the first stream
        $RTSP_STREAM_LISTENED_TO = 1;
    }

    //The RTSP streams contain 'RTSP_X' in the filename, were X is the stream url index in the comma separated list of RTSP streams
    //We can use this to locate the file for this stream
    foreach ($files as $file_idx => $stream_file_name) {
        //Skip the folder hierarchy entries
        if ($stream_file_name != "." && $stream_file_name != "..") {
            //See if the filename contains the correct RTSP name, also only check .wav.json files
            if (stripos($stream_file_name, 'RTSP_' . $RTSP_STREAM_LISTENED_TO) !== false && stripos($stream_file_name, '.wav.json') !== false) {
                //Found a match - set it as the newest file
                $newest_file = $stream_file_name;
            }
        }
    }
}


//If the newest file param has been supplied and it's the same as the newest file found
//then stop processing
if(isset($_GET['newest_file']) && $newest_file == $_GET['newest_file']) {
  die();
}

// Sanitize filename to prevent path traversal
$newest_file = basename($newest_file);
$contents = file_get_contents($look_in_directory . $newest_file);
if ($contents !== false) {
  $json = json_decode($contents);
  if ($json != null) {
    $datetime = DateTime::createFromFormat(DateTime::ISO8601, $json->{'timestamp'});
    $now = new DateTime();
    $interval = $now->diff($datetime);
    $json->delay = $interval->format('%s');
    echo json_encode($json);
  }
}

//Kill the script so no further processing or output is done
die();
}

// Handle screenshot upload
if(isset($_GET['save_screenshot']) && $_SERVER['REQUEST_METHOD'] === 'POST') {
  header('Content-Type: application/json');
  
  try {
    // Get the RECS_DIR from config
    $RECS_DIR = $config["RECS_DIR"];
    
    // Create screenshots directory if it doesn't exist
    $screenshots_dir = $RECS_DIR . "/Birdsongs - screenshots";
    if (!file_exists($screenshots_dir)) {
      if (!mkdir($screenshots_dir, 0755, true)) {
        throw new Exception("Failed to create screenshots directory");
      }
    }
    
    // Verify the directory is writable
    if (!is_writable($screenshots_dir)) {
      throw new Exception("Screenshots directory is not writable");
    }
    
    // Check if screenshot file was uploaded
    if (!isset($_FILES['screenshot']) || $_FILES['screenshot']['error'] !== UPLOAD_ERR_OK) {
      throw new Exception("No screenshot file uploaded or upload error");
    }
    
    // Validate file type
    $file_info = finfo_open(FILEINFO_MIME_TYPE);
    $mime_type = finfo_file($file_info, $_FILES['screenshot']['tmp_name']);
    finfo_close($file_info);
    
    if ($mime_type !== 'image/png') {
      throw new Exception("Invalid file type. Expected PNG image.");
    }
    
    // Get timestamp from POST data or use current time
    $timestamp = isset($_POST['timestamp']) ? preg_replace('/[^0-9_-]/', '', $_POST['timestamp']) : date('Y-m-d_H-i-s');
    
    // Construct filename
    $filename = "spectrogram_" . $timestamp . ".png";
    $filepath = $screenshots_dir . "/" . $filename;
    
    // Move uploaded file
    if (!move_uploaded_file($_FILES['screenshot']['tmp_name'], $filepath)) {
      throw new Exception("Failed to save screenshot file");
    }
    
    // Success response - return only filename, not full path
    echo json_encode([
      'success' => true,
      'filename' => $filename
    ]);
    
  } catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
      'success' => false,
      'error' => $e->getMessage()
    ]);
  }
  
  die();
}


//Hold the array of RTSP steams once they are exploded
$RTSP_Stream_Config = array();

//Load the birdnet config so we can read the RTSP setting
// Valid config data
if (is_array($config) && array_key_exists('RTSP_STREAM',$config)) {
	if (is_null($config['RTSP_STREAM']) === false && $config['RTSP_STREAM'] !== "") {
		$RTSP_Stream_Config_Data = explode(",", $config['RTSP_STREAM']);

		//Process the stream further
		//we need to able to ID it (just do this by position), get the hostname to show in the dropdown box
		foreach ($RTSP_Stream_Config_Data as $stream_idx => $stream_url) {
			//$stream_idx is the array position of the the RSP stream URL, idx of 0 is the first, 1 - second etc
			$RTSP_stream_url = parse_url($stream_url);
			$RTSP_Stream_Config[$stream_idx] = $RTSP_stream_url['host'];
		}
	}
}

?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vertical Spectrogram</title>
  <style>
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  background: hsl(280, 100%, 10%);
  font-family: 'Roboto Flex', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

#main-container {
  display: flex;
  height: 100%;
  width: 100%;
}

#canvas-container {
  position: relative;
  flex: 1;
  height: 100%;
  max-width: 100%;
  margin: 0;
}

#frequency-labels-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
  /* Use crisp edges for better spectrogram clarity */
  image-rendering: -moz-crisp-edges;          /* Firefox */
  image-rendering: crisp-edges;               /* Standard */
}

#loading-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 24px;
  font-weight: bold;
  text-align: center;
  z-index: 10;
}

.sidebar {
  width: 240px;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
  color: white;
  font-size: 14px;
  overflow-y: scroll;
  padding: 15px;
  box-shadow: -2px 0 10px rgba(0, 0, 0, 0.5);
  z-index: 20;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
  padding-bottom: 6px;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.button-group {
  display: flex;
  gap: 5px;
}

.control-button {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 3px;
  padding: 4px 8px;
  color: white;
  cursor: pointer;
  font-size: 10px;
  transition: background 0.2s ease;
}

.control-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.sidebar-content > div {
  margin: 8px 0;
}

.sidebar-content label {
  display: block;
  margin-bottom: 3px;
  font-weight: 500;
  font-size: 11px;
}

.sidebar-content input[type="range"] {
  width: 100%;
  margin: 3px 0;
}

.sidebar-content input[type="checkbox"] {
  margin-right: 6px;
  width: 14px;
  height: 14px;
  cursor: pointer;
  vertical-align: middle;
}

.sidebar-content select {
  width: 100%;
  padding: 4px;
  border-radius: 3px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.5);
  color: white;
  cursor: pointer;
  font-size: 11px;
}

.value-display {
  display: inline-block;
  min-width: 40px;
  text-align: right;
  font-weight: bold;
  font-size: 11px;
  color: #4CAF50;
}

.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  vertical-align: middle;
  margin-left: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.hidden {
  display: none !important;
}

.control-group {
  background: rgba(255, 255, 255, 0.05);
  padding: 6px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.control-group-title {
  font-size: 10px;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
  font-weight: 600;
}

.size-input {
  width: 100%;
  padding: 4px;
  border-radius: 3px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.5);
  color: white;
  font-size: 11px;
}

/* Mobile optimizations */
@media only screen and (max-width: 768px) {
  #main-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    height: auto;
    max-height: 40vh;
    order: 2;
  }
  
  #canvas-container {
    max-width: 100%;
    order: 1;
    flex: 1;
  }
  
  #loading-message {
    font-size: 18px;
  }
}

@media only screen and (max-width: 768px) and (orientation: landscape) {
  .sidebar {
    max-height: 50vh;
  }
}
  </style>
</head>
<body>
  <div id="main-container">
    <div id="canvas-container">
      <div id="loading-message">Loading Vertical Spectrogram...</div>
      <canvas id="spectrogram-canvas"></canvas>
      <canvas id="frequency-labels-overlay"></canvas>
    </div>

    <div class="sidebar" id="sidebar-panel">
      <div class="sidebar-header">
        <h3>Spectrogram Controls</h3>
        <div class="button-group">
          <button class="control-button" id="new-tab-button" title="Open in New Tab" aria-label="Open in New Tab">↗</button>
          <button class="control-button" id="fullscreen-button" title="Toggle Fullscreen" aria-label="Toggle Fullscreen Mode">⛶</button>
        </div>
      </div>
      <div class="sidebar-content">
    <?php
    if (isset($RTSP_Stream_Config) && !empty($RTSP_Stream_Config)) {
      ?>
      <div class="control-group">
        <div class="control-group-title">Stream Selection</div>
        <div>
          <label>RTSP Stream:</label>
          <select id="rtsp-stream-select">
          <?php
          //The setting representing which livestream to stream is more than the number of RTSP streams available
          //maybe the list of streams has been modified
          if (isset($config['RTSP_STREAM_TO_LIVESTREAM']) && array_key_exists($config['RTSP_STREAM_TO_LIVESTREAM'], $RTSP_Stream_Config) === false) {
            $contents = file_get_contents('/etc/birdnet/birdnet.conf');
            if ($contents !== false) {
              $contents = preg_replace("/RTSP_STREAM_TO_LIVESTREAM=.*/", "RTSP_STREAM_TO_LIVESTREAM=\"0\"", $contents);
              $fh = fopen("/etc/birdnet/birdnet.conf", "w");
              if ($fh !== false) {
                fwrite($fh, $contents);
                fclose($fh);
                get_config($force_reload=true);
                exec("sudo systemctl restart livestream.service");
              } else {
                error_log("Failed to open /etc/birdnet/birdnet.conf for writing");
              }
            } else {
              error_log("Failed to read /etc/birdnet/birdnet.conf");
            }
          }

          //Print out the dropdown list for the RTSP streams
          foreach ($RTSP_Stream_Config as $stream_id => $stream_host) {
            $isSelected = "";
            //Match up the selected value saved in config so we can preselect it
            if (isset($config['RTSP_STREAM_TO_LIVESTREAM']) && $config['RTSP_STREAM_TO_LIVESTREAM'] == $stream_id) {
              $isSelected = 'selected="selected"';
            }
            //Create the select option - escape output to prevent XSS
            echo "<option value=\"" . htmlspecialchars($stream_id, ENT_QUOTES, 'UTF-8') . "\" $isSelected>" . htmlspecialchars($stream_host, ENT_QUOTES, 'UTF-8') . "</option>";
          }
          ?>
        </select>
        <span id="rtsp-spinner" class="spinner" style="display: none;"></span>
      </div>
    </div>
      <?php
    }
    ?>
    <div class="control-group">
      <div class="control-group-title">Audio Settings</div>
      <div>
        <label>Gain:</label>
        <input type="range" id="gain-slider" min="0" max="250" value="100" />
        <span class="value-display" id="gain-value">100%</span>
      </div>
      <div>
        <label>
          <input type="checkbox" id="compression-checkbox" />
          Compression
        </label>
      </div>
      <div>
        <label>
          <input type="checkbox" id="freqshift-checkbox" <?php echo ($config['ACTIVATE_FREQSHIFT_IN_LIVESTREAM'] == "true") ? "checked" : ""; ?> />
          Freq Shift
        </label>
        <span id="freqshift-spinner" class="spinner" style="display: none;"></span>
      </div>
    </div>
    <div class="control-group">
      <div class="control-group-title">Display Settings</div>
      <div>
        <label>Redraw Interval:</label>
        <input type="range" id="redraw-slider" min="50" max="300" value="100" step="10" />
        <span class="value-display" id="redraw-value">100ms</span>
      </div>
      <div>
        <label>Color Scheme:</label>
        <select id="color-scheme-select">
          <option value="purple" selected>Purple</option>
          <option value="blackwhite">Black-White</option>
          <option value="lava">Lava</option>
          <option value="greenwhite">Green-White</option>
        </select>
      </div>
      <div>
        <label>
          <input type="checkbox" id="frequency-grid-checkbox" checked />
          Show Frequency Grid
        </label>
      </div>
    </div>
    <div class="control-group">
      <div class="control-group-title">Canvas Size</div>
      <div>
        <label>Width (px):</label>
        <input type="number" id="canvas-width-input" min="200" max="2000" value="600" step="50" class="size-input" />
      </div>
      <div style="margin-top: 8px;">
        <label>Height (px):</label>
        <input type="number" id="canvas-height-input" min="200" max="2000" value="800" step="50" class="size-input" />
      </div>
      <div style="margin-top: 8px;">
        <button class="control-button" id="apply-size-button" style="width: 100%; padding: 8px;">Apply Size</button>
      </div>
    </div>
    <div class="control-group">
      <div class="control-group-title">Detection Filters</div>
      <div>
        <label>Min Confidence:</label>
        <input type="range" id="confidence-slider" min="10" max="100" value="70" step="5" />
        <span class="value-display" id="confidence-value">70%</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px;">
        <label style="flex: 1;">Rotate Labels:</label>
        <button class="control-button" id="rotate-labels-button" title="Rotate detection labels" aria-label="Rotate detection labels">&#8635;</button>
        <span class="value-display" id="rotation-value">-90°</span>
      </div>
    </div>
    <div class="control-group">
      <div class="control-group-title">Frequency Filter</div>
      <div>
        <label>
          <input type="checkbox" id="lowcut-checkbox" />
          Low-Cut Filter
        </label>
      </div>
      <div id="lowcut-controls" class="hidden">
        <label>Cutoff Frequency:</label>
        <input type="range" id="lowcut-slider" min="50" max="1500" value="200" step="10" />
        <span class="value-display" id="lowcut-value">200Hz</span>
      </div>
    </div>
    </div>
  </div>
  </div>

  <!-- Hidden audio element for stream -->
  <audio id="audio-player" style="display:none" crossorigin="anonymous" preload="none">
    <source src="stream">
  </audio>

  <!-- Load vertical spectrogram script -->
  <script src="../static/vertical-spectrogram.js"></script>

  <script>
    // Configuration from PHP
    const FREQSHIFT_RECONNECT_DELAY = <?php echo $FREQSHIFT_RECONNECT_DELAY; ?>;
    const ROTATION_INCREMENT = Math.PI / 2;
    const RAD_TO_DEG = 180 / Math.PI;
    let labelRotation;

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
      if (!window.VerticalSpectrogram || !VerticalSpectrogram.CONFIG) {
        console.error('VerticalSpectrogram unavailable; cannot initialize controls');
        return;
      }

      labelRotation = (typeof VerticalSpectrogram.CONFIG.LABEL_ROTATION === 'number')
        ? VerticalSpectrogram.CONFIG.LABEL_ROTATION
        : -ROTATION_INCREMENT;

      const canvas = document.getElementById('spectrogram-canvas');
      const audioPlayer = document.getElementById('audio-player');
      const loadingMessage = document.getElementById('loading-message');

      // Setup audio player
      audioPlayer.addEventListener('canplay', function() {
        console.log('Audio ready, initializing spectrogram...');
        
        // Hide loading message
        loadingMessage.style.display = 'none';
        
        // Initialize vertical spectrogram
        try {
          VerticalSpectrogram.initialize(canvas, audioPlayer);
          console.log('Vertical spectrogram initialized successfully');
        } catch (error) {
          console.error('Failed to initialize spectrogram:', error);
          loadingMessage.textContent = 'Error loading spectrogram';
          loadingMessage.style.display = 'block';
        }
      });

      audioPlayer.addEventListener('error', function(e) {
        console.error('Audio player error:', e);
        loadingMessage.textContent = 'Error loading audio stream';
      });

      // Start audio playback
      audioPlayer.load();
      audioPlayer.play().catch(function(error) {
        console.log('Autoplay prevented, user interaction required:', error);
        loadingMessage.textContent = 'Click to start';
        loadingMessage.style.cursor = 'pointer';
        loadingMessage.addEventListener('click', function() {
          audioPlayer.play().then(function() {
            console.log('Audio playback started');
          });
        });
      });

      // Setup controls
      setupControls();
      setupControlButtons();
      
      // Load saved settings
      loadSettings();
    });

    function updateRotationValue() {
      const rotationValue = document.getElementById('rotation-value');
      if (rotationValue) {
        rotationValue.textContent = Math.round(labelRotation * RAD_TO_DEG) + '\u00B0';
      }
    }

    // Settings persistence using localStorage
    const SETTINGS_KEY = 'verticalSpectrogramSettings';
    
    function saveSettings() {
      try {
        const settings = {
          gain: document.getElementById('gain-slider')?.value,
          compression: document.getElementById('compression-checkbox')?.checked,
          redrawInterval: document.getElementById('redraw-slider')?.value,
          colorScheme: document.getElementById('color-scheme-select')?.value,
          frequencyGrid: document.getElementById('frequency-grid-checkbox')?.checked,
          canvasWidth: document.getElementById('canvas-width-input')?.value,
          canvasHeight: document.getElementById('canvas-height-input')?.value,
          minConfidence: document.getElementById('confidence-slider')?.value,
          lowCutEnabled: document.getElementById('lowcut-checkbox')?.checked,
          lowCutFrequency: document.getElementById('lowcut-slider')?.value,
          labelRotation: labelRotation
        };
        
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
        console.log('Settings saved:', settings);
      } catch (error) {
        console.error('Failed to save settings:', error);
      }
    }
    
    function loadSettings() {
      try {
        const savedSettings = localStorage.getItem(SETTINGS_KEY);
        if (!savedSettings) {
          console.log('No saved settings found');
          updateRotationValue();
          return;
        }
        
        const settings = JSON.parse(savedSettings);
        console.log('Loading saved settings:', settings);
        
        // Apply gain
        if (settings.gain !== undefined) {
          const gainSlider = document.getElementById('gain-slider');
          const gainValue = document.getElementById('gain-value');
          if (gainSlider && gainValue) {
            gainSlider.value = settings.gain;
            gainValue.textContent = settings.gain + '%';
            VerticalSpectrogram.setGain((settings.gain / 100) * 2);
          }
        }
        
        // Apply compression
        if (settings.compression !== undefined) {
          const compressionCheckbox = document.getElementById('compression-checkbox');
          if (compressionCheckbox) {
            compressionCheckbox.checked = settings.compression;
          }
        }
        
        // Apply redraw interval
        if (settings.redrawInterval !== undefined) {
          const redrawSlider = document.getElementById('redraw-slider');
          const redrawValue = document.getElementById('redraw-value');
          if (redrawSlider && redrawValue) {
            redrawSlider.value = settings.redrawInterval;
            redrawValue.textContent = settings.redrawInterval + 'ms';
            VerticalSpectrogram.updateConfig({
              REDRAW_INTERVAL_MS: parseInt(settings.redrawInterval)
            });
          }
        }
        
        // Apply color scheme
        if (settings.colorScheme !== undefined) {
          const colorSchemeSelect = document.getElementById('color-scheme-select');
          if (colorSchemeSelect) {
            colorSchemeSelect.value = settings.colorScheme;
            VerticalSpectrogram.setColorScheme(settings.colorScheme);
          }
        }
        
        // Apply frequency grid
        if (settings.frequencyGrid !== undefined) {
          const frequencyGridCheckbox = document.getElementById('frequency-grid-checkbox');
          if (frequencyGridCheckbox) {
            frequencyGridCheckbox.checked = settings.frequencyGrid;
            VerticalSpectrogram.updateConfig({
              SHOW_FREQUENCY_GRID: settings.frequencyGrid
            });
          }
        }
        
        // Apply canvas size and trigger resize
        if (settings.canvasWidth !== undefined && settings.canvasHeight !== undefined) {
          const canvasWidthInput = document.getElementById('canvas-width-input');
          const canvasHeightInput = document.getElementById('canvas-height-input');
          const canvasContainer = document.getElementById('canvas-container');
          
          if (canvasWidthInput && canvasHeightInput && canvasContainer) {
            const width = parseInt(settings.canvasWidth);
            const height = parseInt(settings.canvasHeight);
            
            // Validate dimensions before applying
            if (width >= 200 && width <= 2000 && height >= 200 && height <= 2000) {
              canvasWidthInput.value = width;
              canvasHeightInput.value = height;
              
              // Actually apply the canvas size
              canvasContainer.style.width = width + 'px';
              canvasContainer.style.height = height + 'px';
              canvasContainer.style.maxWidth = width + 'px';
              canvasContainer.style.flex = 'none';
              
              // Trigger resize event to update canvas
              window.dispatchEvent(new Event('resize'));
            }
          }
        }
        
        // Apply min confidence
        if (settings.minConfidence !== undefined) {
          const confidenceSlider = document.getElementById('confidence-slider');
          const confidenceValue = document.getElementById('confidence-value');
          if (confidenceSlider && confidenceValue) {
            confidenceSlider.value = settings.minConfidence;
            confidenceValue.textContent = settings.minConfidence + '%';
            VerticalSpectrogram.updateConfig({
              MIN_CONFIDENCE_THRESHOLD: parseInt(settings.minConfidence) / 100
            });
          }
        }
        
        // Apply low-cut filter
        if (settings.lowCutEnabled !== undefined) {
          const lowcutCheckbox = document.getElementById('lowcut-checkbox');
          const lowcutControls = document.getElementById('lowcut-controls');
          if (lowcutCheckbox && lowcutControls) {
            lowcutCheckbox.checked = settings.lowCutEnabled;
            VerticalSpectrogram.setLowCutFilter(settings.lowCutEnabled);
            
            if (settings.lowCutEnabled) {
              lowcutControls.classList.remove('hidden');
            } else {
              lowcutControls.classList.add('hidden');
            }
          }
        }
        
        // Apply low-cut frequency
        if (settings.lowCutFrequency !== undefined) {
          const lowcutSlider = document.getElementById('lowcut-slider');
          const lowcutValue = document.getElementById('lowcut-value');
          if (lowcutSlider && lowcutValue) {
            lowcutSlider.value = settings.lowCutFrequency;
            lowcutValue.textContent = settings.lowCutFrequency + 'Hz';
            VerticalSpectrogram.setLowCutFrequency(parseInt(settings.lowCutFrequency));
          }
        }

        if (settings.labelRotation !== undefined) {
          const parsedRotation = parseFloat(settings.labelRotation);
          if (!isNaN(parsedRotation)) {
            VerticalSpectrogram.setLabelRotation(parsedRotation);
            labelRotation = VerticalSpectrogram.CONFIG.LABEL_ROTATION;
            updateRotationValue();
          }
        } else {
          updateRotationValue();
        }
        
        console.log('Settings loaded successfully');
      } catch (error) {
        console.error('Failed to load settings:', error);
      }
    }

    function setupControlButtons() {
      // New Tab button
      const newTabButton = document.getElementById('new-tab-button');
      newTabButton.addEventListener('click', function() {
        window.open(window.location.href, '_blank');
      });

      // Fullscreen button
      const fullscreenButton = document.getElementById('fullscreen-button');
      fullscreenButton.addEventListener('click', function() {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(err => {
            console.error('Error attempting to enable fullscreen:', err);
          });
        } else {
          document.exitFullscreen();
        }
      });
    }

    function setupControls() {
      // Gain control
      const gainSlider = document.getElementById('gain-slider');
      const gainValue = document.getElementById('gain-value');
      gainSlider.addEventListener('input', function() {
        const value = this.value / 100;
        gainValue.textContent = this.value + '%';
        VerticalSpectrogram.setGain(value * 2); // Scale to 0-2 range
        saveSettings();
      });

      // Compression control (not yet implemented in vertical spectrogram)
      const compressionCheckbox = document.getElementById('compression-checkbox');
      compressionCheckbox.addEventListener('change', function() {
        console.log('Compression:', this.checked);
        // TODO: Implement compression if needed
        saveSettings();
      });

      // Frequency shift control
      const freqshiftCheckbox = document.getElementById('freqshift-checkbox');
      const freqshiftSpinner = document.getElementById('freqshift-spinner');
      freqshiftCheckbox.addEventListener('change', function() {
        toggleFreqshift(this.checked);
      });

      // Redraw interval control
      const redrawSlider = document.getElementById('redraw-slider');
      const redrawValue = document.getElementById('redraw-value');
      redrawSlider.addEventListener('input', function() {
        const value = parseInt(this.value);
        redrawValue.textContent = value + 'ms';
        VerticalSpectrogram.updateConfig({
          REDRAW_INTERVAL_MS: value
        });
        saveSettings();
      });

      // Confidence threshold control
      const confidenceSlider = document.getElementById('confidence-slider');
      const confidenceValue = document.getElementById('confidence-value');
      confidenceSlider.addEventListener('input', function() {
        const value = parseInt(this.value) / 100;
        confidenceValue.textContent = this.value + '%';
        VerticalSpectrogram.updateConfig({
          MIN_CONFIDENCE_THRESHOLD: value
        });
        saveSettings();
      });

      // setLabelRotation normalizes rotation to [-π, π] like the horizontal spectrogram
      const rotateLabelsButton = document.getElementById('rotate-labels-button');
      if (rotateLabelsButton) {
        rotateLabelsButton.addEventListener('click', function() {
          VerticalSpectrogram.setLabelRotation(labelRotation - ROTATION_INCREMENT);
          labelRotation = VerticalSpectrogram.CONFIG.LABEL_ROTATION;
          updateRotationValue();
          saveSettings();
        });
      }

      // Color scheme selector
      const colorSchemeSelect = document.getElementById('color-scheme-select');
      colorSchemeSelect.addEventListener('change', function() {
        VerticalSpectrogram.setColorScheme(this.value);
        saveSettings();
      });

      // Frequency grid toggle
      const frequencyGridCheckbox = document.getElementById('frequency-grid-checkbox');
      frequencyGridCheckbox.addEventListener('change', function() {
        VerticalSpectrogram.updateConfig({
          SHOW_FREQUENCY_GRID: this.checked
        });
        saveSettings();
      });

      // Low-cut filter control
      const lowcutCheckbox = document.getElementById('lowcut-checkbox');
      const lowcutControls = document.getElementById('lowcut-controls');
      const lowcutSlider = document.getElementById('lowcut-slider');
      const lowcutValue = document.getElementById('lowcut-value');
      
      lowcutCheckbox.addEventListener('change', function() {
        VerticalSpectrogram.setLowCutFilter(this.checked);
        // Show/hide frequency slider when filter is enabled
        if (this.checked) {
          lowcutControls.classList.remove('hidden');
        } else {
          lowcutControls.classList.add('hidden');
        }
        saveSettings();
      });
      
      lowcutSlider.addEventListener('input', function() {
        const value = parseInt(this.value);
        lowcutValue.textContent = value + 'Hz';
        VerticalSpectrogram.setLowCutFrequency(value);
        saveSettings();
      });

      // Canvas size controls
      const canvasWidthInput = document.getElementById('canvas-width-input');
      const canvasHeightInput = document.getElementById('canvas-height-input');
      const applySizeButton = document.getElementById('apply-size-button');
      
      // Set initial values from current canvas size
      const canvasContainer = document.getElementById('canvas-container');
      canvasWidthInput.value = canvasContainer.clientWidth;
      canvasHeightInput.value = canvasContainer.clientHeight;
      
      applySizeButton.addEventListener('click', function() {
        const width = parseInt(canvasWidthInput.value);
        const height = parseInt(canvasHeightInput.value);
        
        // Validate dimensions
        if (isNaN(width) || width < 200 || width > 2000) {
          alert('Width must be between 200 and 2000 pixels.');
          return;
        }
        if (isNaN(height) || height < 200 || height > 2000) {
          alert('Height must be between 200 and 2000 pixels.');
          return;
        }
        
        canvasContainer.style.width = width + 'px';
        canvasContainer.style.height = height + 'px';
        canvasContainer.style.maxWidth = width + 'px';
        canvasContainer.style.flex = 'none';
        
        // Trigger resize event to update canvas
        window.dispatchEvent(new Event('resize'));
        
        // Save settings after applying size
        saveSettings();
      });

      // RTSP stream selector
      const rtspSelect = document.getElementById('rtsp-stream-select');
      if (rtspSelect) {
        const rtspSpinner = document.getElementById('rtsp-spinner');
        rtspSelect.addEventListener('change', function() {
          if (this.value !== undefined) {
            rtspSpinner.style.display = 'inline-block';
            const xhr = new XMLHttpRequest();
            xhr.open('GET', 'views.php?rtsp_stream_to_livestream=' + this.value + '&view=Advanced&submit=advanced');
            xhr.send();
            xhr.onload = function() {
              if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
                setTimeout(function() {
                  const audioPlayer = document.getElementById('audio-player');
                  audioPlayer.pause();
                  audioPlayer.load();
                  audioPlayer.play();
                  rtspSpinner.style.display = 'none';
                }, <?php echo RTSP_STREAM_RECONNECT_DELAY; ?>);
              }
            };
          }
        });
      }

      VerticalSpectrogram.setLabelRotation(labelRotation);
      updateRotationValue();
    }

    function toggleFreqshift(state) {
      const freqshiftSpinner = document.getElementById('freqshift-spinner');
      freqshiftSpinner.style.display = 'inline-block';
      
      const xhr = new XMLHttpRequest();
      xhr.open('GET', 'views.php?activate_freqshift_in_livestream=' + state + '&view=Advanced&submit=advanced');
      xhr.send();
      
      xhr.onload = function() {
        if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
          setTimeout(function() {
            const audioPlayer = document.getElementById('audio-player');
            audioPlayer.pause();
            audioPlayer.load();
            audioPlayer.play();
            freqshiftSpinner.style.display = 'none';
          }, FREQSHIFT_RECONNECT_DELAY);
        }
      };
    }
  </script>
</body>
</html>
