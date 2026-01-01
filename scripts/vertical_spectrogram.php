<?php
error_reporting(E_ERROR);
ini_set('display_errors',1);

require_once "scripts/common.php";
$home = get_home();
$config = get_config();

if(!empty($config['FREQSHIFT_RECONNECT_DELAY']) && is_numeric($config['FREQSHIFT_RECONNECT_DELAY'])){
    $FREQSHIFT_RECONNECT_DELAY = ($config['FREQSHIFT_RECONNECT_DELAY']);
}else{
    $FREQSHIFT_RECONNECT_DELAY = 4000;
}

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
if($newest_file == $_GET['newest_file']) {
  die();
}

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

#canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
}

canvas {
  display: block;
  width: 100%;
  height: 100%;
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

.controls {
  position: absolute;
  top: 10px;
  left: 10px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  padding: 15px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  z-index: 20;
  max-width: 90%;
}

.controls > div {
  margin: 8px 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.controls label {
  margin-right: 10px;
  font-weight: 500;
  min-width: 80px;
}

.controls input[type="range"] {
  flex: 1;
  min-width: 100px;
  margin: 0 10px;
}

.controls input[type="checkbox"] {
  margin-left: 5px;
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.controls select {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.5);
  color: white;
  cursor: pointer;
}

.controls .value-display {
  min-width: 40px;
  text-align: right;
  font-weight: bold;
}

.spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  vertical-align: middle;
  margin-left: 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Mobile optimizations */
@media only screen and (max-width: 768px) {
  .controls {
    font-size: 12px;
    padding: 10px;
    top: 5px;
    left: 5px;
  }
  
  .controls label {
    min-width: 60px;
    font-size: 11px;
  }
  
  .controls input[type="range"] {
    min-width: 80px;
  }
  
  #loading-message {
    font-size: 18px;
  }
}

@media only screen and (max-width: 768px) and (orientation: landscape) {
  .controls {
    font-size: 11px;
    padding: 8px;
  }
}
  </style>
</head>
<body>
  <div id="canvas-container">
    <div id="loading-message">Loading Vertical Spectrogram...</div>
    <canvas id="spectrogram-canvas"></canvas>
  </div>

  <div class="controls">
    <?php
    if (isset($RTSP_Stream_Config) && !empty($RTSP_Stream_Config)) {
      ?>
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
      <?php
    }
    ?>
    <div>
      <label>Gain:</label>
      <input type="range" id="gain-slider" min="0" max="250" value="100" />
      <span class="value-display" id="gain-value">100%</span>
    </div>
    <div>
      <label>Compression:</label>
      <input type="checkbox" id="compression-checkbox" />
    </div>
    <div>
      <label>Freq Shift:</label>
      <input type="checkbox" id="freqshift-checkbox" <?php echo ($config['ACTIVATE_FREQSHIFT_IN_LIVESTREAM'] == "true") ? "checked" : ""; ?> />
      <span id="freqshift-spinner" class="spinner" style="display: none;"></span>
    </div>
    <div>
      <label>Redraw (ms):</label>
      <input type="range" id="redraw-slider" min="50" max="300" value="100" step="10" />
      <span class="value-display" id="redraw-value">100ms</span>
    </div>
    <div>
      <label>Min Confidence:</label>
      <input type="range" id="confidence-slider" min="10" max="100" value="70" step="5" />
      <span class="value-display" id="confidence-value">70%</span>
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

    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
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
    });

    function setupControls() {
      // Gain control
      const gainSlider = document.getElementById('gain-slider');
      const gainValue = document.getElementById('gain-value');
      gainSlider.addEventListener('input', function() {
        const value = this.value / 100;
        gainValue.textContent = this.value + '%';
        VerticalSpectrogram.setGain(value * 2); // Scale to 0-2 range
      });

      // Compression control (not yet implemented in vertical spectrogram)
      const compressionCheckbox = document.getElementById('compression-checkbox');
      compressionCheckbox.addEventListener('change', function() {
        console.log('Compression:', this.checked);
        // TODO: Implement compression if needed
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
                }, 10000);
              }
            };
          }
        });
      }
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
