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

if(isset($_GET['ajax_csv'])) {
  $RECS_DIR = $config["RECS_DIR"];
  $STREAM_DATA_DIR = $RECS_DIR . "/StreamData/";

  if (empty($config['RTSP_STREAM'])) {
    $look_in_directory = $STREAM_DATA_DIR;
    $files = scandir($look_in_directory, SCANDIR_SORT_ASCENDING);
    //Extract the filename, positions 0 and 1 are the folder hierarchy '.' and '..'
    $newest_file = $files[2];
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
            //See if the filename contains the correct RTSP name, also only check .wav.csv files
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
<script>  
// CREDITS: https://codepen.io/jakealbaugh/pen/jvQweW

// UPDATE: there is a problem in chrome with starting audio context
//  before a user gesture. This fixes it.
var started = null;
var player = null;
var gain = 128;
const ctx = null;
let fps =[];
let avgfps;
let requestTime;
const FULL_TURN = Math.PI * 2;
const HALF_TURN = Math.PI;
const ROTATION_INCREMENT = Math.PI / 2;
const RAD_TO_DEG = 180 / Math.PI;
let labelRotation = -ROTATION_INCREMENT;

<?php 
if(isset($_GET['legacy']) && $_GET['legacy'] == "true") {
  echo "var legacy = true;";
} else {
  echo "var legacy = false;";
}
?>

window.onload = function(){
  var playersrc =  document.getElementById('playersrc');
  playersrc.onerror = function() {
    window.location="views.php?view=Spectrogram&legacy=true";
  };

  // if user agent includes iPhone or Mac use legacy mode
  if(window.navigator.userAgent.includes("iPhone") || legacy == true) {
    document.getElementById("spectrogramimage").style.display="";
    document.body.querySelector('canvas').remove();
    document.getElementById('player').remove();
    document.body.querySelector('h1').remove();
    document.getElementsByClassName("centered")[0].remove()

    <?php 
  $refresh = $config['RECORDING_LENGTH'];
  $time = time();
  ?>
    // every $refresh seconds, this loop will run and refresh the spectrogram image
  window.setInterval(function(){
    document.getElementById("spectrogramimage").src = "spectrogram.png?nocache="+Date.now();
  }, <?php echo $refresh; ?>*1000);
  } else {
    document.getElementById("spectrogramimage").remove();

  var audioelement =  window.parent.document.getElementsByTagName("audio")[0];
  if (typeof(audioelement) != 'undefined') {

    document.getElementById('player').remove();

    player = audioelement;
    if (started) return;
    started = true;
    initialize();
  } else {
    player = document.getElementById('player');
    player.oncanplay = function() {
      if (started) return;
        started = true;
        initialize();
    };
  }
  player.play();
  
  }
};

function fitTextOnCanvas(text,fontface,yPosition){    
    var fontsize=300;
    do{
        fontsize--;
        CTX.font=fontsize+"px "+fontface;
    }while(CTX.measureText(text).width>document.body.querySelector('canvas').width)
    CTX.font = CTX.font=(fontsize*0.35)+"px "+fontface;
    CTX.fillText(text,document.body.querySelector('canvas').width - (document.body.querySelector('canvas').width * 0.50),yPosition);
}

// Configuration for detection labels
const DETECTION_CONFIG = {
  MIN_CONFIDENCE_THRESHOLD: 0.7,
  CONFIDENCE_HIGH_COLOR: 'rgb(50, 255, 50)', // Bright green
  CONFIDENCE_MEDIUM_COLOR: 'rgb(255, 165, 0)', // Orange
  CONFIDENCE_LOW_COLOR: 'rgba(180, 180, 180, 0.6)', // Light gray
  CONFIDENCE_THRESHOLD_RANGE: 0.05, // ±5%
  CONFIDENCE_LOW_OFFSET: 0.10, // 10% below
  NAME_COLOR: 'rgba(255, 255, 255, 0.9)'
};

// Get color for confidence level
function getConfidenceColor(confidence, threshold) {
  const diff = confidence - threshold;
  
  if (diff >= 0) {
    return DETECTION_CONFIG.CONFIDENCE_HIGH_COLOR;
  } else if (Math.abs(diff) <= DETECTION_CONFIG.CONFIDENCE_THRESHOLD_RANGE) {
    return DETECTION_CONFIG.CONFIDENCE_MEDIUM_COLOR;
  } else if (Math.abs(diff) <= DETECTION_CONFIG.CONFIDENCE_LOW_OFFSET) {
    return DETECTION_CONFIG.CONFIDENCE_LOW_COLOR;
  } else {
    return null; // Don't show
  }
}

function applyText(text, x, y, confidence) {
  console.log("conf: " + confidence);
  console.log(text + " " + parseInt(x) + " " + y);
  
  // Check if we should show this detection
  const confidenceColor = getConfidenceColor(confidence, DETECTION_CONFIG.MIN_CONFIDENCE_THRESHOLD);
  if (!confidenceColor) {
    return; // Don't show detections more than 10% below threshold
  }
  
  // Save context state
  CTX.save();
  
  // Get canvas element (cached in the rendering context)
  const canvasEl = document.body.querySelector('canvas');
  
  // Position at bottom of canvas and rotate by the selected amount
  const bottomY = canvasEl.height - 10;
  CTX.translate(parseInt(x), bottomY);
  CTX.rotate(labelRotation);
  
  // Draw species name in white
  CTX.textAlign = "right";
  CTX.font = '13px Roboto Flex';
  CTX.fillStyle = DETECTION_CONFIG.NAME_COLOR;
  CTX.fillText(text, 0, 0);
  
  // Measure name text to position confidence
  const nameWidth = CTX.measureText(text).width;
  const spaceWidth = CTX.measureText(' ').width;
  
  // Draw confidence in color
  const confidencePercent = '+' + Math.round(confidence * 100) + '%';
  CTX.fillStyle = confidenceColor;
  CTX.fillText(confidencePercent, -(nameWidth + spaceWidth), 0);
  
  // Restore context state
  CTX.restore();
  
  CTX.fillStyle = 'hsl(280, 100%, 10%)';
}

var add=0;
var newest_file;
var recentDetections = []; // Track recent detections for filtering

function loadDetectionIfNewExists() {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    // if there's a new detection that needs to be updated to the page
    if(this.responseText.length > 0 && !this.responseText.includes("Database")) {
      const resp = JSON.parse(this.responseText);
      newest_file = resp.file_name;
      console.log("delay " + resp.delay);
      
      // Group detections by timestamp to identify multi-detections
      const detectionGroups = {};
      resp.detections.forEach(detection => {
        const key = Math.floor(detection.start * 10); // Group by 0.1s intervals
        if (!detectionGroups[key]) {
          detectionGroups[key] = [];
        }
        detectionGroups[key].push(detection);
      });
      
      // Clean up old recent detections (older than 2 seconds)
      const now = Date.now() / 1000; // Convert to seconds
      recentDetections = recentDetections.filter(d => (now - d.timestamp) < 2);
      
      // Process each detection group
      Object.values(detectionGroups).forEach(group => {
        const isMultiDetection = group.length > 1;
        
        group.forEach(detection => {
          // Check for rapid consecutive single detections (not multi-detections)
          if (!isMultiDetection) {
            const isDuplicate = recentDetections.some(recent => 
              recent.name === detection.common_name &&
              Math.abs(recent.start - detection.start) < 2.0
            );
            
            if (isDuplicate) {
              console.log("Skipping rapid consecutive detection: " + detection.common_name);
              return; // Skip this detection
            }
          }
          
          console.log("detection.start  " + detection.start);
          secago = resp.delay - detection.start;
          x = document.body.querySelector('canvas').width - (secago * avgfps);
          y = (document.body.querySelector('canvas').height * 0.50) + add;
          
          if(x > document.body.querySelector('canvas').width - (5*avgfps) && detection.common_name.length > 8) {
            setTimeout(function (detection, x, y, x_org) {
              console.log("originally at "+x_org+", now waiting 3 sec and at "+x);
              applyText(detection.common_name, x, y, detection.confidence);
            }, 3*1000, detection, x - (5*avgfps), y, x);
          } else {
            applyText(detection.common_name, x, y, detection.confidence);
          }
          
          // Track this detection
          recentDetections.push({
            name: detection.common_name,
            start: detection.start,
            timestamp: now
          });
          
          // stagger Y placement
          add+= 15;
          if(add >= 60) {
             add = 0;
          }
        });
      });
    }
  };
  xhttp.open("GET", "spectrogram.php?ajax_csv=true&newest_file="+newest_file, true);
  xhttp.send();
}

window.setInterval(function(){
   loadDetectionIfNewExists();
}, 1000);

var compressor = undefined;
var SOURCE;
var ACTX;
var ANALYSER;
var gainNode;

function toggleCompression(state) {
  //var biquadFilter = ACTX.createBiquadFilter();
  //biquadFilter.type = "highpass";
 // biquadFilter.frequency.setValueAtTime(13000, ACTX.currentTime);
  if(state == true) {
    SOURCE.disconnect(gainNode)
    gainNode.disconnect(ANALYSER);
    gainNode.disconnect(ACTX.destination);
    SOURCE.connect(compressor);
    compressor.connect(ANALYSER);
    ANALYSER.connect(gainNode);
    gainNode.connect(ACTX.destination);
    //biquadFilter.connect(ANALYSER);
    //biquadFilter.connect(ACTX.destination);
  } else {
    SOURCE.disconnect(compressor);
    compressor.disconnect(ANALYSER);
    ANALYSER.disconnect(gainNode);
    gainNode.disconnect(ACTX.destination);
    SOURCE.connect(gainNode);
    gainNode.connect(ANALYSER);
    gainNode.connect(ACTX.destination);
  }
}

function toggleFreqshift(state) {
  if (state == true) {
    console.log("freqshift activated")
  } else {
    console.log("freqshift deactivated")
  }

  freqShiftReconnectDelay = <?php echo $FREQSHIFT_RECONNECT_DELAY; ?>;

  var livestream_freqshift_spinner = document.getElementById('livestream_freqshift_spinner');
  livestream_freqshift_spinner.style.display = "inline"; 
  // Create the XMLHttpRequest object.
  const xhr = new XMLHttpRequest();
  // Initialize the request
  xhr.open("GET", 'views.php?activate_freqshift_in_livestream=' + state + '&view=Advanced&submit=advanced');
  // Send the request
  xhr.send();
  // Fired once the request completes successfully
  xhr.onload = function (e) {
    // Check if the request was a success
    if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
      // Restart the audio player in case it stopped working while the livestream service was restarted
      var audio_player = document.querySelector('audio#player');
      if (audio_player !== 'undefined') {
        //central_controls_element.appendChild(h1_loading);
        //Wait 2 seconds before restarting the stream
        setTimeout(function () {
          console.log("Restarting connection with livestream");
          audio_player.pause();
          audio_player.setAttribute('src', 'stream');
          audio_player.load();
          audio_player.play();

          livestream_freqshift_spinner.style.display = "none"; 
        },
        freqShiftReconnectDelay
        )
      }
    }
  }
}

function initialize() {
  document.body.querySelector('h1').remove();
  const CVS = document.body.querySelector('canvas');
  CTX = CVS.getContext('2d');
  const W = CVS.width = window.innerWidth;
  const H = CVS.height = window.innerHeight;

  ACTX = new AudioContext();
  ANALYSER = ACTX.createAnalyser();

  ANALYSER.fftSize = 2048;  
  
  // Handle orientation changes on mobile devices
  window.addEventListener('orientationchange', function() {
    setTimeout(function() {
      CVS.width = window.innerWidth;
      CVS.height = window.innerHeight;
    }, 100);
  });
  
  // Handle window resize
  window.addEventListener('resize', function() {
    CVS.width = window.innerWidth;
    CVS.height = window.innerHeight;
  });
  
  try{
    process();
  } catch(e) {
    console.log(e)
    window.top.location.reload();
  }



  function process() {
    SOURCE = ACTX.createMediaElementSource(player);
    

    compressor = ACTX.createDynamicsCompressor();
    compressor.threshold.setValueAtTime(-50, ACTX.currentTime);
    compressor.knee.setValueAtTime(40, ACTX.currentTime);
    compressor.ratio.setValueAtTime(12, ACTX.currentTime);
    compressor.attack.setValueAtTime(0, ACTX.currentTime);
    compressor.release.setValueAtTime(0.25, ACTX.currentTime);
    gainNode = ACTX.createGain();
    gainNode.gain = 1;
    SOURCE.connect(gainNode);
    gainNode.connect(ANALYSER);
    gainNode.connect(ACTX.destination);

    document.getElementById("compression").removeAttribute("disabled");
    document.getElementById("freqshift").removeAttribute("disabled");

    console.log(SOURCE);
    const DATA = new Uint8Array(ANALYSER.frequencyBinCount);
    const LEN = DATA.length;
    const h = (H / LEN + 0.9);
    const x = W - 1;
    CTX.fillStyle = 'hsl(280, 100%, 10%)';
    CTX.fillRect(0, 0, W, H);

    // Define frequency lines to draw (in Hz)
    // These will be drawn as horizontal lines across the spectrogram
    const SAMPLE_RATE = 48000; // Standard audio sample rate
    const NYQUIST = SAMPLE_RATE / 2; // Maximum frequency
    const FREQUENCY_LINES = [1000, 2000, 3000, 4000, 5000, 6000, 8000, 10000, 12000]; // Hz
    
    // Function to draw frequency grid lines
    function drawFrequencyLines() {
      if (!showGrid) return; // Skip if grid is disabled
      
      CTX.save();
      CTX.strokeStyle = 'rgba(128, 128, 128, 0.3)'; // Medium gray with lower opacity
      CTX.lineWidth = 1;
      CTX.setLineDash([5, 5]);
      
      FREQUENCY_LINES.forEach(freq => {
        if (freq <= NYQUIST) {
          // Calculate Y position for this frequency
          const binIndex = (freq / NYQUIST) * LEN;
          const y = H - (binIndex * h);
          
          // Draw horizontal line
          CTX.beginPath();
          CTX.moveTo(0, y);
          CTX.lineTo(W, y);
          CTX.stroke();
          
          // Draw frequency label
          CTX.fillStyle = 'rgba(180, 180, 180, 0.6)'; // Light gray for labels
          CTX.font = '10px Roboto Flex';
          CTX.textAlign = 'left';
          CTX.fillText(freq >= 1000 ? (freq/1000) + 'kHz' : freq + 'Hz', 5, y - 2);
        }
      });
      
      CTX.restore();
    }
    
    // Draw initial frequency lines
    drawFrequencyLines();

    loop();

    function loop(time) {
      if (requestTime) {
          fpsval = Math.round(1000/((performance.now() - requestTime)))
          if(fpsval > 0){
              fps.push( fpsval);
          }
      }
      if(fps.length > 0){
          avgfps = fps.reduce((a, b) => a + b) / fps.length;
      }
      requestTime = time;
      window.requestAnimationFrame((timeRes) => loop(timeRes));
      let imgData = CTX.getImageData(1, 0, W - 1, H);

      CTX.fillRect(0, 0, W, H);
      CTX.putImageData(imgData, 0, 0);
      
      // Redraw frequency lines after scrolling
      drawFrequencyLines();
      
      ANALYSER.getByteFrequencyData(DATA);
      for (let i = 0; i < LEN; i++) {
        let rat = DATA[i] / 255 ;
        let hue = Math.round((rat * 120) + 280 % 360);
        let sat = '100%';
        let lit = 10 + (70 * rat) + '%';
        CTX.beginPath();
        CTX.strokeStyle = `hsl(${hue}, ${sat}, ${lit})`;
        CTX.moveTo(x, H - (i * h));
        CTX.lineTo(x, H - (i * h + h));
        CTX.stroke();
      }
    }
  }
}

</script>
<style>
html, body {
  height: 100%;
}

canvas {
  display: block;
  height: 85%;
  width: 100%;
}

h1 {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  margin: 0;
}

/* Mobile landscape orientation optimizations */
@media only screen and (max-width: 768px) and (orientation: landscape) {
  canvas {
    height: 75%;
  }
  
  .centered {
    font-size: 0.8em;
    padding: 5px 0;
  }
  
  .centered label {
    font-size: 0.9em;
  }
  
  .centered input[type="range"] {
    width: 60px;
    height: 25px;
  }
  
  .centered select {
    font-size: 0.85em;
    padding: 3px;
  }
  
  .centered input[type="checkbox"] {
    width: 18px;
    height: 18px;
  }
  
  /* Make controls more touch-friendly */
  .centered > div {
    margin: 0 5px;
  }
}

/* Mobile portrait orientation optimizations */
@media only screen and (max-width: 768px) and (orientation: portrait) {
  canvas {
    height: 80%;
  }
  
  .centered {
    font-size: 0.85em;
    flex-wrap: wrap;
  }
  
  .centered > div {
    margin: 5px 3px;
  }
  
  .centered input[type="checkbox"] {
    width: 18px;
    height: 18px;
  }
}

/* Tablet landscape orientation */
@media only screen and (min-width: 769px) and (max-width: 1024px) and (orientation: landscape) {
  canvas {
    height: 82%;
  }
  
  .centered {
    padding: 8px 0;
  }
}

.control-section {
  background: rgba(0, 0, 0, 0.7);
  padding: 10px;
  margin-bottom: 5px;
  border-radius: 4px;
}

.control-section label {
  font-weight: 500;
  margin-right: 5px;
}

.control-section input[type="number"],
.control-section input[type="range"],
.control-section select {
  margin: 0 5px;
}

.control-section button {
  padding: 4px 10px;
  margin-left: 5px;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 3px;
}

.control-section button:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>

<img id="spectrogramimage" style="width:100%;height:100%;display:none" src="spectrogram.png?nocache=<?php echo $time;?>">

<div class="control-section centered" style="font-size: 0.9em;">
  <div style="display:inline; margin-right: 15px;">
    <label>Width:</label>
    <input type="number" id="canvas-width" min="400" max="3000" value="0" step="50" style="width: 80px;" />
  </div>
  <div style="display:inline; margin-right: 15px;">
    <label>Height:</label>
    <input type="number" id="canvas-height" min="300" max="2000" value="0" step="50" style="width: 80px;" />
  </div>
  <div style="display:inline; margin-right: 15px;">
    <button id="apply-canvas-size">Apply Size</button>
    <button id="reset-canvas-size">Reset</button>
  </div>
  &mdash;
  <div style="display:inline; margin-right: 15px;">
    <label>Min Confidence:</label>
    <input type="range" id="confidence-threshold" min="10" max="100" value="70" step="5" style="width: 100px;" />
    <span id="confidence-value">70%</span>
  </div>
  &mdash;
  <div style="display:inline; margin-right: 15px;">
    <label title="Rotate detection labels">Rotate text:</label>
    <button id="rotate-labels" title="Rotate detection labels" aria-label="Rotate detection labels">&#8635;</button>
    <span id="rotation-value" aria-live="polite">-90°</span>
  </div>
  &mdash;
  <div style="display:inline;">
    <label>
      <input type="checkbox" id="show-frequency-grid" checked />
      Frequency Grid
    </label>
  </div>
</div>

<div class="centered">
	<?php
	if (isset($RTSP_Stream_Config) && !empty($RTSP_Stream_Config)) {
		?>
        <div style="display:inline" id="RTSP_streams">
            <label>RTSP Stream: </label>
            <select id="rtsp_stream_select" class="testbtn" name="RTSP Streams">
				<?php
				//The setting representing which livestream to stream is more than the number of RTSP streams available
				//maybe the list of streams has been modified
                //This isn't the ideal for this, but needed a way to fix this setting without calling the advanced setting page
				if (array_key_exists($config['RTSP_STREAM_TO_LIVESTREAM'], $RTSP_Stream_Config) === false) {
					$contents = file_get_contents('/etc/birdnet/birdnet.conf');
					$contents = preg_replace("/RTSP_STREAM_TO_LIVESTREAM=.*/", "RTSP_STREAM_TO_LIVESTREAM=\"0\"", $contents);
					$fh = fopen("/etc/birdnet/birdnet.conf", "w");
					fwrite($fh, $contents);
					get_config($force_reload=true);
					exec("sudo systemctl restart livestream.service");
				}

				//Print out the dropdown list for the RTSP streams
				foreach ($RTSP_Stream_Config as $stream_id => $stream_host) {
					$isSelected = "";
					//Match up the selected value saved in config so we can preselect it
					if ($config['RTSP_STREAM_TO_LIVESTREAM'] == $stream_id) {
						$isSelected = 'selected="selected"';
					}
					//Create the select option
					echo "<option value=" . $stream_id . " $isSelected >" . $stream_host . "</option>";
				}

				?>
            </select>
        </div>
        &mdash;
		<?php
	}
	?>
  <div style="display:inline" id="gain" >
  <label>Gain: </label>
  <span class="slidecontainer">
    <input name="gain_input" type="range" min="0" max="250" value="100" class="slider" id="gain_input">
    <span id="gain_value"></span>%
  </span>
  </div>
    &mdash;
  <div style="display:inline" id="comp" >
    <label>Compression: </label>
    <input name="compression" type="checkbox" id="compression" disabled>
  </div>
  <div style="display:inline" id="fshift" >
    <label>Freq shift: </label>
    <?php 
        if ($config['ACTIVATE_FREQSHIFT_IN_LIVESTREAM'] == "true") {
          $freqshift_state = "checked";
        } else {
          $freqshift_state = "";
        }
    ?>
    <input name="freqshift" type="checkbox" id="freqshift" <?php echo($freqshift_state); ?>  disabled>
    <img id="livestream_freqshift_spinner" src=images/spinner.gif style="height: 25px; vertical-align: top; display: none">
  </div>
</div>

<audio style="display:none" controls="" crossorigin="anonymous" id='player' preload="none"><source id="playersrc" src="stream"></audio>
<h1 id="loading-h1">Loading...</h1>
<canvas></canvas>

<script>
var rtsp_stream_select = document.getElementById("rtsp_stream_select");
if (typeof (rtsp_stream_select) !== 'undefined' && rtsp_stream_select !== null) {
    //When the dropdown selection is changed set the new value is settings, then restart the livestream service so it broadcasts newly selected RTSP stream
    rtsp_stream_select.onchange = function () {
        if (this.value !== 'undefined') {
            // Get the audio player element
            var audio_player = document.querySelector('audio#player');
            var central_controls_element = document.getElementsByClassName('centered')[0];

            //Create the loading header again as a placeholder while we're waiting to reload the stream
            var h1_loading = document.createElement("H1");
            var h1_loading_text = document.createTextNode("Loading...");
            h1_loading.setAttribute("id", "loading-h1");
            h1_loading.setAttribute("style", "font-size:48px; font-weight: bolder; color: #FFF");
            h1_loading.appendChild(h1_loading_text);

            // Create the XMLHttpRequest object.
            const xhr = new XMLHttpRequest();
            // Initialize the request
            xhr.open("GET", 'views.php?rtsp_stream_to_livestream=' + this.value + '&view=Advanced&submit=advanced');
            // Send the request
            xhr.send();
            // Fired once the request completes successfully
            xhr.onload = function (e) {
                // Check if the request was a success
                if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
                    // Restart the audio player in case it stopped working while the livestream service was restarted
                    if (audio_player !== 'undefined') {
                        central_controls_element.appendChild(h1_loading);
                        //Wait 5 seconds before restarting the stream
                        setTimeout(function () {
                                audio_player.pause();
                                audio_player.setAttribute('src', 'stream');
                                audio_player.load();
                                audio_player.play();

                                document.getElementById('loading-h1').remove()
                            },
                            10000
                        )
                    }
                }
            }
        }
    }
}

var slider = document.getElementById("gain_input");
var output = document.getElementById("gain_value");
output.innerHTML = slider.value; // Display the default slider value

// Update the current slider value (each time you drag the slider handle)
slider.oninput = function() {
  output.innerHTML = this.value;
  gainNode.gain.setValueAtTime((this.value/(100/2)), ACTX.currentTime);
  gain=Math.abs(this.value - 255);
}

var compression = document.getElementById("compression");
compression.onclick = function() {
  toggleCompression(this.checked);
}

var freqshift = document.getElementById("freqshift");
freqshift.onclick = function() {
  toggleFreqshift(this.checked);
}

// Canvas size controls
var canvasWidthInput = document.getElementById("canvas-width");
var canvasHeightInput = document.getElementById("canvas-height");
var applyCanvasSizeBtn = document.getElementById("apply-canvas-size");
var resetCanvasSizeBtn = document.getElementById("reset-canvas-size");
var canvasElement = document.body.querySelector('canvas');

// Set initial values from current canvas size
canvasWidthInput.value = window.innerWidth;
canvasHeightInput.value = window.innerHeight;

applyCanvasSizeBtn.onclick = function() {
  var width = parseInt(canvasWidthInput.value);
  var height = parseInt(canvasHeightInput.value);
  
  // Validate dimensions
  if (isNaN(width) || width < 400 || width > 3000) {
    alert('Width must be between 400 and 3000 pixels.');
    return;
  }
  if (isNaN(height) || height < 300 || height > 2000) {
    alert('Height must be between 300 and 2000 pixels.');
    return;
  }
  
  // Set canvas size using style properties
  if (canvasElement) {
    canvasElement.style.width = width + 'px';
    canvasElement.style.height = height + 'px';
    canvasElement.width = width;
    canvasElement.height = height;
  }
};

resetCanvasSizeBtn.onclick = function() {
  canvasWidthInput.value = window.innerWidth;
  canvasHeightInput.value = window.innerHeight;
  if (canvasElement) {
    canvasElement.style.width = '100%';
    canvasElement.style.height = '85%';
    canvasElement.width = window.innerWidth;
    canvasElement.height = window.innerHeight;
  }
};

// Confidence threshold control
var confidenceSlider = document.getElementById("confidence-threshold");
var confidenceValue = document.getElementById("confidence-value");

confidenceSlider.oninput = function() {
  confidenceValue.textContent = this.value + '%';
  DETECTION_CONFIG.MIN_CONFIDENCE_THRESHOLD = parseInt(this.value) / 100;
};

// Rotation control
var rotateLabelsBtn = document.getElementById("rotate-labels");
var rotationValue = document.getElementById("rotation-value");

function normalizeRotation(value) {
  let normalizedValue = value % FULL_TURN;
  if (normalizedValue <= -HALF_TURN) {
    normalizedValue += FULL_TURN;
  } else if (normalizedValue > HALF_TURN) {
    normalizedValue -= FULL_TURN;
  }
  return normalizedValue;
}

function updateRotationValue() {
  if (rotationValue) {
    var degrees = Math.round(labelRotation * RAD_TO_DEG);
    rotationValue.textContent = degrees + '\u00B0';
  }
}

if (rotateLabelsBtn) {
  rotateLabelsBtn.onclick = function() {
    labelRotation = normalizeRotation(labelRotation - ROTATION_INCREMENT);
    updateRotationValue();
  };
}

updateRotationValue();

// Frequency grid toggle
var showFrequencyGrid = document.getElementById("show-frequency-grid");
var showGrid = true;

showFrequencyGrid.onclick = function() {
  showGrid = this.checked;
};
</script>
