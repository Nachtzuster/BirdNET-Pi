<?php
ini_set('display_errors', 1);
error_reporting(E_ERROR);

require_once "scripts/common.php";
$home = get_home();
$config = get_config();

ensure_authenticated();

if(isset($_GET['submit'])) {
  $contents = file_get_contents('/etc/birdnet/birdnet.conf');
  $restart_livestream = false;
  $update_caddyfile = false;

  if(isset($_GET["caddy_pwd"])) {
    $caddy_pwd = $_GET["caddy_pwd"];
    if(strcmp($caddy_pwd,$config['CADDY_PWD']) !== 0) {
      $contents = preg_replace("/CADDY_PWD=.*/", "CADDY_PWD=\"$caddy_pwd\"", $contents);
      $update_caddyfile = true;
    }
  }

  if(isset($_GET["ice_pwd"])) {
    $ice_pwd = $_GET["ice_pwd"];
    if(strcmp($ice_pwd,$config['ICE_PWD']) !== 0) {
      $contents = preg_replace("/ICE_PWD=.*/", "ICE_PWD=$ice_pwd", $contents);
      $restart_livestream = true;
    }
  }

  if(isset($_GET["birdnetpi_url"])) {
    $birdnetpi_url = $_GET["birdnetpi_url"];
    // remove trailing slash to prevent conf from becoming broken
    $birdnetpi_url = rtrim($birdnetpi_url, '/');
    if(strcmp($birdnetpi_url,$config['BIRDNETPI_URL']) !== 0) {
      $contents = preg_replace("/BIRDNETPI_URL=.*/", "BIRDNETPI_URL=$birdnetpi_url", $contents);
      $update_caddyfile = true;
    }
  }

  if(isset($_GET["rtsp_stream"])) {
    $rtsp_stream = str_replace("\r\n", ",", $_GET["rtsp_stream"]);
    if(strcmp($rtsp_stream,$config['RTSP_STREAM']) !== 0) {
      $contents = preg_replace("/RTSP_STREAM=.*/", "RTSP_STREAM=\"$rtsp_stream\"", $contents);
      $restart_livestream = True;
    }
  }

  if (isset($_GET["rtsp_stream_to_livestream"])) {
    $rtsp_stream_selected = trim($_GET["rtsp_stream_to_livestream"]);

    //Setting exists already, see if the value changed
    if (strcmp($rtsp_stream_selected, $config['RTSP_STREAM_TO_LIVESTREAM']) !== 0) {
      $contents = preg_replace("/RTSP_STREAM_TO_LIVESTREAM=.*/", "RTSP_STREAM_TO_LIVESTREAM=\"$rtsp_stream_selected\"", $contents);
      $restart_livestream = True;
    }
  }

  if (isset($_GET["activate_freqshift_in_livestream"])) {
    $activate_freqshift_in_livestream = trim($_GET["activate_freqshift_in_livestream"]);

    //Setting exists already, see if the value changed
    if (strcmp($activate_freqshift_in_livestream, $config['ACTIVATE_FREQSHIFT_IN_LIVESTREAM']) !== 0) {
      $contents = preg_replace("/ACTIVATE_FREQSHIFT_IN_LIVESTREAM=.*/", "ACTIVATE_FREQSHIFT_IN_LIVESTREAM=\"$activate_freqshift_in_livestream\"", $contents);
      $restart_livestream = True;
    }
  }
  
  if(isset($_GET["overlap"])) {
    $overlap = $_GET["overlap"];
    if(strcmp($overlap,$config['OVERLAP']) !== 0) {
      $contents = preg_replace("/OVERLAP=.*/", "OVERLAP=$overlap", $contents);
    }
  }

  if(isset($_GET["confidence"])) {
    $confidence = $_GET["confidence"];
    if(strcmp($confidence,$config['CONFIDENCE']) !== 0) {
      $contents = preg_replace("/CONFIDENCE=.*/", "CONFIDENCE=$confidence", $contents);
    }
  }

  if(isset($_GET["sensitivity"])) {
    $sensitivity = $_GET["sensitivity"];
    if(strcmp($sensitivity,$config['SENSITIVITY']) !== 0) {
      $contents = preg_replace("/SENSITIVITY=.*/", "SENSITIVITY=$sensitivity", $contents);
    }
  }

  if(isset($_GET["freqshift_hi"]) && is_numeric($_GET['freqshift_hi'])) {
    $freqshift_hi = $_GET["freqshift_hi"];
    if(strcmp($freqshift_hi,$config['FREQSHIFT_HI']) !== 0) {
      $contents = preg_replace("/FREQSHIFT_HI=.*/", "FREQSHIFT_HI=$freqshift_hi", $contents);
    }
  }

  if(isset($_GET["freqshift_lo"]) && is_numeric($_GET['freqshift_lo'])) {
    $freqshift_lo = $_GET["freqshift_lo"];
    if(strcmp($freqshift_lo,$config['FREQSHIFT_LO']) !== 0) {
      $contents = preg_replace("/FREQSHIFT_LO=.*/", "FREQSHIFT_LO=$freqshift_lo", $contents);
    }
  }

  if(isset($_GET["freqshift_pitch"]) && is_numeric($_GET['freqshift_pitch'])) {
    $freqshift_pitch = $_GET["freqshift_pitch"];
    if(strcmp($freqshift_pitch,$config['FREQSHIFT_PITCH']) !== 0) {
      $contents = preg_replace("/FREQSHIFT_PITCH=.*/", "FREQSHIFT_PITCH=$freqshift_pitch", $contents);
    }
  }

  if(isset($_GET["freqshift_tool"])) {
    $freqshift_tool = $_GET["freqshift_tool"];
    if(strcmp($freqshift_tool,$config['FREQSHIFT_TOOL']) !== 0) {
      $contents = preg_replace("/FREQSHIFT_TOOL=.*/", "FREQSHIFT_TOOL=$freqshift_tool", $contents);
    }
  }

  if(isset($_GET["freqshift_reconnect_delay"]) && is_numeric($_GET['freqshift_reconnect_delay'])) {
    $freqshift_reconnect_delay = $_GET["freqshift_reconnect_delay"];
    if(strcmp($freqshift_hi,$config['FREQSHIFT_RECONNECT_DELAY']) !== 0) {
      $contents = preg_replace("/FREQSHIFT_RECONNECT_DELAY=.*/", "FREQSHIFT_RECONNECT_DELAY=$freqshift_reconnect_delay", $contents);
    }
  }

  if(isset($_GET["full_disk"])) {
    $full_disk = $_GET["full_disk"];
    if(strcmp($full_disk,$config['FULL_DISK']) !== 0) {
      $contents = preg_replace("/FULL_DISK=.*/", "FULL_DISK=$full_disk", $contents);
    }
  }

if (isset($_GET["max_files_species"])) {
    $max_files_species = $_GET["max_files_species"];
    if (strcmp($max_files_species, $config['MAX_FILES_SPECIES']) !== 0) {
        $contents = preg_replace("/MAX_FILES_SPECIES=.*/", "MAX_FILES_SPECIES=$max_files_species", $contents);
    }
}
	
  if(isset($_GET["privacy_threshold"])) {
    $privacy_threshold = $_GET["privacy_threshold"];
    if(strcmp($privacy_threshold,$config['PRIVACY_THRESHOLD']) !== 0) {
      $contents = preg_replace("/PRIVACY_THRESHOLD=.*/", "PRIVACY_THRESHOLD=$privacy_threshold", $contents);
    }
  }

  if(isset($_GET["rec_card"])) {
    $rec_card = $_GET["rec_card"];
    if(strcmp($rec_card,$config['REC_CARD']) !== 0) {
      $contents = preg_replace("/REC_CARD=.*/", "REC_CARD=\"$rec_card\"", $contents);
    }
  }

  if(isset($_GET["channels"])) {
    $channels = $_GET["channels"];
    if(strcmp($channels,$config['CHANNELS']) !== 0) {
      $contents = preg_replace("/CHANNELS=.*/", "CHANNELS=$channels", $contents);
    }
  }

  if(isset($_GET["recording_length"])) {
    $recording_length = $_GET["recording_length"];
    if(strcmp($recording_length,$config['RECORDING_LENGTH']) !== 0) {
      $contents = preg_replace("/RECORDING_LENGTH=.*/", "RECORDING_LENGTH=$recording_length", $contents);
    }
  }

  if(isset($_GET["extraction_length"])) {
    $extraction_length = $_GET["extraction_length"];
    if(strcmp($extraction_length,$config['EXTRACTION_LENGTH']) !== 0) {
      $contents = preg_replace("/EXTRACTION_LENGTH=.*/", "EXTRACTION_LENGTH=$extraction_length", $contents);
    }
  }

  if(isset($_GET["audiofmt"])) {
    $audiofmt = $_GET["audiofmt"];
    if(strcmp($audiofmt,$config['AUDIOFMT']) !== 0) {
      $contents = preg_replace("/AUDIOFMT=.*/", "AUDIOFMT=$audiofmt", $contents);
    }
  }
  if(isset($_GET["silence_update_indicator"])) {
    $silence_update_indicator = 1;
    if(strcmp($silence_update_indicator,$config['SILENCE_UPDATE_INDICATOR']) !== 0) {
      $contents = preg_replace("/SILENCE_UPDATE_INDICATOR=.*/", "SILENCE_UPDATE_INDICATOR=$silence_update_indicator", $contents);
    }
  } else {
    $contents = preg_replace("/SILENCE_UPDATE_INDICATOR=.*/", "SILENCE_UPDATE_INDICATOR=0", $contents);
  }

  if(isset($_GET["raw_spectrogram"])) {
    $raw_spectrogram = 1;
    if(strcmp($RAW_SPECTROGRAM,$config['RAW_SPECTROGRAM']) !== 0) {
      $contents = preg_replace("/RAW_SPECTROGRAM=.*/", "RAW_SPECTROGRAM=$raw_spectrogram", $contents);
    }
  } else {
    $contents = preg_replace("/RAW_SPECTROGRAM=.*/", "RAW_SPECTROGRAM=0", $contents);
  }

  if(isset($_GET["custom_image"])) {
    $custom_image = $_GET["custom_image"];
    if(strcmp($custom_image,$config['CUSTOM_IMAGE']) !== 0) {
      $contents = preg_replace("/CUSTOM_IMAGE=.*/", "CUSTOM_IMAGE=$custom_image", $contents);
    }
  }

  if(isset($_GET["custom_image_label"])) {
    $custom_image_label = $_GET["custom_image_label"];
    if(strcmp($custom_image_label,$config['CUSTOM_IMAGE_TITLE']) !== 0) {
      $contents = preg_replace("/CUSTOM_IMAGE_TITLE=.*/", "CUSTOM_IMAGE_TITLE=\"$custom_image_label\"", $contents);
    }
  }

  if (isset($_GET["LogLevel_BirdnetRecordingService"])) {
    $birdnet_recording_service_log_level = trim($_GET["LogLevel_BirdnetRecordingService"]);
	if (strcmp($birdnet_recording_service_log_level, $config['LogLevel_BirdnetRecordingService']) !== 0) {
		$contents = preg_replace("/LogLevel_BirdnetRecordingService=.*/", "LogLevel_BirdnetRecordingService=\"$birdnet_recording_service_log_level\"", $contents);
	}
  }
  if (isset($_GET["LogLevel_SpectrogramViewerService"])) {
    $spectrogram_viewer_service_log_level = trim($_GET["LogLevel_SpectrogramViewerService"]);
	if (strcmp($spectrogram_viewer_service_log_level, $config['LogLevel_SpectrogramViewerService']) !== 0) {
		$contents = preg_replace("/LogLevel_SpectrogramViewerService=.*/", "LogLevel_SpectrogramViewerService=\"$spectrogram_viewer_service_log_level\"", $contents);
	}
  }
  if (isset($_GET["LogLevel_LiveAudioStreamService"])) {
    $livestream_audio_service_log_level = trim($_GET["LogLevel_LiveAudioStreamService"]);
	if (strcmp($livestream_audio_service_log_level, $config['LogLevel_LiveAudioStreamService']) !== 0) {
		$contents = preg_replace("/LogLevel_LiveAudioStreamService=.*/", "LogLevel_LiveAudioStreamService=\"$livestream_audio_service_log_level\"", $contents);
		$restart_livestream = True;
	}
  }

  //Finally write the data out. some sections do this themselves in order to have the new settings ready for the services that will be restarted
  //but will doubly ensure the settings are saved after any modification
  $fh = fopen('/etc/birdnet/birdnet.conf', "w");
  fwrite($fh, $contents);
  $config = get_config($force_reload=true);

  syslog(LOG_INFO, "Restarting Services");
  if ($update_caddyfile){
      exec('sudo /usr/local/bin/update_caddyfile.sh > /dev/null 2>&1 &');
  }
  shell_exec("sudo restart_services.sh");
  if ($restart_livestream) {
    exec("sudo systemctl restart livestream.service");
  }
}

$count_labels = count(file($home."/BirdNET-Pi/model/labels.txt"));
$count = $count_labels;
?>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  </style>
  </head>
<div class="settings">

<?php
$newconfig = get_config();
?>
      <div class="brbanner"><h1>Advanced Settings</h1></div><br>
    <form id="advancedform" action="" method="GET">
      <table class="settingstable"><tr><td>
      <h2>Privacy Threshold</h2>
      <div class="slidecontainer">
        <input name="privacy_threshold" type="range" min="0" max="3" value="<?php print($newconfig['PRIVACY_THRESHOLD']);?>" class="slider" id="privacy_threshold">
        <p>Value: <span id="threshold_value"></span>%</p>
      </div>
      <script>
      var slider = document.getElementById("privacy_threshold");
      var output = document.getElementById("threshold_value");
      output.innerHTML = slider.value; // Display the default slider value
      
      // Update the current slider value (each time you drag the slider handle)
      slider.oninput = function() {
        output.innerHTML = this.value;
        document.getElementById("predictionCount").innerHTML = parseInt(Math.max(10, (this.value * <?php echo $count; ?>)/100));
      }
      </script>
      <p>If a Human is predicted anywhere among the top <span id="predictionCount"><?php echo intval(max(10, ($newconfig['PRIVACY_THRESHOLD'] * $count)/100)); ?></span> predictions, the sample will be considered of human origin and no data will be collected. Start with 1% and move up as needed.</p>
      </td></tr></table><br>
      
      <table class="settingstable"><tr><td>
      <h2>Disk Management</h2>
      <label for="purge">
      <input name="full_disk" type="radio" id="purge" value="purge" <?php if (strcmp($newconfig['FULL_DISK'], "purge") == 0) { echo "checked"; }?>>Purge</label>
      <label for="keep">
      <input name="full_disk" type="radio" id="keep" value="keep" <?php if (strcmp($newconfig['FULL_DISK'], "keep") == 0) { echo "checked"; }?>>Keep</label>
      <p>When the disk becomes full, you can choose to 'purge' old files to make room for new ones or 'keep' your data and stop all services instead.<br>Note: you can exclude specific files from 'purge' on the Recordings page.</p>
      <br>
      <label for="max_files_species">Amount of files to keep for each species :</label>
      <input name="max_files_species" type="number" style="width:6em;" min="0" step="1" value="<?php print($newconfig['MAX_FILES_SPECIES']);?>"/>
      </td></tr><tr><td>
      If different than 0 (keep all), defines the maximum number of files to be kept for each species, with priority give to files with highest confidence. 
      This value does not take into account the last 7 days (protected by default).
      </td></tr><tr><td>
      Note only the spectrogram and audio files are deleted, the obsevation data remains in the database.
      The files protected through the "lock" icon are also not affected.
      </td></tr></table><br>
      <table class="settingstable"><tr><td>

      <h2>Audio Settings</h2>
      <label for="rec_card">Audio Card: </label>
      <input name="rec_card" type="text" size="12" value="<?php print($newconfig['REC_CARD']);?>" required/><br>
      Set Audio Card to 'default' to use PulseAudio (always recommended), or an ALSA recognized sound card device from the output of `arecord -L`. Choose the `dsnoop` device if it is available.<br><br>
      <label for="channels">Audio Channels: </label>
      <input name="channels" type="number" style="width:3em;" min="1" max="32" step="1" value="<?php print($newconfig['CHANNELS']);?>" required/><br>
      Set Channels to the number of channels supported by your sound card. 32 max.<br><br>
      <label for="recording_length">Recording Length: </label>
      <input name="recording_length" oninput="document.getElementsByName('extraction_length')[0].setAttribute('max', this.value);" type="number" style="width:3em;" min="3" max="60" step="1" value="<?php print($newconfig['RECORDING_LENGTH']);?>" required/><br>
      Set Recording Length in seconds between 6 and 60. Multiples of 3 are recommended, as BirdNET analyzes in 3-second chunks.<br><br> 
      <label for="extraction_length">Extraction Length: </label>
      <input name="extraction_length" oninput="this.setAttribute('max', document.getElementsByName('recording_length')[0].value);" type="number" style="width:3em;" min="3" value="<?php print($newconfig['EXTRACTION_LENGTH']);?>" /><br>
      Set Extraction Length to something less than your Recording Length. Min=3 Max=Recording Length<br><br>
      <label for="audiofmt">Extractions Audio Format</label>
      <select name="audiofmt" class="testbtn">
      <option selected="<?php print($newconfig['AUDIOFMT']);?>"><?php print($newconfig['AUDIOFMT']);?></option>
<?php
  $formats = array("8svx", "aif", "aifc", "aiff", "aiffc", "al", "amb", "amr-nb", "amr-wb", "anb", "au", "avr", "awb", "caf", "cdda", "cdr", "cvs", "cvsd", "cvu", "dat", "dvms", "f32", "f4", "f64", "f8", "fap", "flac", "fssd", "gsm", "gsrt", "hcom", "htk", "ima", "ircam", "la", "lpc", "lpc10", "lu", "mat", "mat4", "mat5", "maud", "mp2", "mp3", "nist", "ogg", "paf", "prc", "pvf", "raw", "s1", "s16", "s2", "s24", "s3", "s32", "s4", "s8", "sb", "sd2", "sds", "sf", "sl", "sln", "smp", "snd", "sndfile", "sndr", "sndt", "sou", "sox", "sph", "sw", "txw", "u1", "u16", "u2", "u24", "u3", "u32", "u4", "u8", "ub", "ul", "uw", "vms", "voc", "vorbis", "vox", "w64", "wav", "wavpcm", "wv", "wve", "xa", "xi");
foreach($formats as $format){
  echo "<option value='$format'>$format</option>";
}
?>
      </select>
      <br><br>
      
      <label id="rtsp_stream_input_label" for="rtsp_stream">RTSP Stream: </label>
      <br>
      <input style="display: none;" name="rtsp_stream" type="url" value="">
      <input style="display: none;" id="rtsp_stream_url_placeholder" name="rtsp_stream_placeholder" type="url" size="60" value="">
        <?php
        //Print out the rtsp urls in their own input fields
		//Explode the stream into an array at the comma
		$rtsp_streams = explode(",", $newconfig['RTSP_STREAM']);
		//Print out existing streams
		foreach ($rtsp_streams as $stream_idx => $stream_url) {
            //For the first input keep the element mostly the same as the original but without styling to align it
			if ($stream_idx === 0) {
				?>
                <input id="rtsp_stream_url_0" name="rtsp_stream_0" type="url" size="60" value="<?php echo $stream_url; ?>">
                <br>
				<?php
			} else {
                //For every other input field, change the id to reflect the URL's index in the array
				?>
                <input id="rtsp_stream_url_<?php echo $stream_idx; ?>" name="rtsp_stream_<?php echo $stream_idx; ?>" type="url" size="60"
                       value="<?php echo $stream_url; ?>">
                <br>
				<?php
			}
		}
        ?>
      <div id="newrtspstream_button_container">
        <br>
        <span id="newrtspstream" onclick="addNewrtspInput();">Add</span><br>
      </div>
      <script>
                      //Keep track of how many new input fields were added
                      var number_of_new_rtsp_urls_added = 0;

                      //Function to insert new input fields
                      function addNewrtspInput() {
                          //Find the placeholder input field
                          var url_template_element = document.getElementById('rtsp_stream_url_placeholder');
                          var new_url_input_template = url_template_element.cloneNode();
                          var br_seperator = document.createElement("BR");

                          //Fix up the new element so it's visible, set the style so it's sligned correctly
                          new_url_input_template.setAttribute("id", "rtsp_stream_url_new_" + number_of_new_rtsp_urls_added);
                          new_url_input_template.setAttribute("name", "rtsp_stream_new_" + number_of_new_rtsp_urls_added);
                          new_url_input_template.removeAttribute("style");

                          //Insert the new input field before the button to add new urls
                          var newrtspstream_button = document.getElementById('newrtspstream_button_container');
                          //Insert the new input element before the newrtspstream button
                          newrtspstream_button.parentNode.insertBefore(new_url_input_template, newrtspstream_button);
                          //Add a separator before the button
                          newrtspstream_button.parentNode.insertBefore(br_seperator, newrtspstream_button);

                          //Increment the counter
                          number_of_new_rtsp_urls_added++;
                      }

                      var rtsp_stream_string = "";
                      var rtsp_stream_string_array = [];

                      //Collect all the rtsp urls that have been set, concat them into a single string and set it into the rtsp_stream input field so it gets saved
                      function collectrtspUrls() {
                          //Reset the array and string so we don't get duplicates
                          rtsp_stream_string = "";
                          rtsp_stream_string_array = [];

                          //Get the inputs by name (which is similar across
                          var existing_rtsp_stream_urls = document.querySelectorAll('[name^="rtsp_stream_"]');
                          //Loop over the result and get the values
                          for (let i = 0; i < existing_rtsp_stream_urls.length; i++) {
                              //Only collect results that re not empty and add them to the array
                              if (existing_rtsp_stream_urls[i].value !== 'undefined' && existing_rtsp_stream_urls[i].value !== "") {
                                  rtsp_stream_string_array.push(existing_rtsp_stream_urls[i].value.trim());
                              }
                          }

                          //if the array is not empty, then implode the array joining all the values by a comma
                          if (rtsp_stream_string_array.length !== 0) {
                              rtsp_stream_string = rtsp_stream_string_array.join(',');
                              //Locate the hidden rtsp_stream input field that we'll populate with the full string which will get saved to the config file
                              var rtsp_stream_input = document.querySelector('[name=rtsp_stream]');
                              rtsp_stream_input.setAttribute('value', rtsp_stream_string);
                          }
                      }
      </script>
      <p>If you place an RTSP stream URL here, BirdNET-Pi will use that as its audio source.<br>Multiple streams are allowed but may have a impact on rPi performance.<br>Analyze ffmpeg CPU/Memory usage with <b>top</b> or <b>htop</b> if necessary.<br>To remove all and use the soundcard again, just delete the RTSP entries and click Save at the bottom.</p>
      </td></tr></table><br>
      <table class="settingstable"><tr><td>
      <h2>BirdNET-Pi Password</h2>
      <p>This password will protect your "Tools" page and "Live Audio" stream.</p>
      <p>Do NOT use special characters. Accepted characters: [A-Z0-9a-z]</p>
      <label for="caddy_pwd">Password: </label>
      <input style="width:40ch" name="caddy_pwd" id="caddy_pwd" type="password" pattern="[A-Za-z0-9]+" title="Password must be alphanumeric (A-Z, 0-9)" value="<?php print($newconfig['CADDY_PWD']);?>" /><span id="showpassword" onmouseover="document.getElementById('caddy_pwd').type='text';" onmouseout="document.getElementById('caddy_pwd').type='password';">show</span><br>
      </td></tr></table><br>
      <table class="settingstable"><tr><td>
      <h2>Custom URL</h2>
      <p>When you update the URL below, the web server will reload, so be sure to wait at least 30 seconds and then go to your new URL.</p>
      <label for="birdnetpi_url">BirdNET-Pi URL: </label>
      <input style="width:40ch;" name="birdnetpi_url" type="url" value="<?php print($newconfig['BIRDNETPI_URL']);?>" /><br>
      <p>The BirdNET-Pi URL is how the main page will be reached. If you want your installation to respond to an IP address, place that here, but be sure to indicate "<i>http://</i>".<br>Example for IP: <i>http://192.168.0.109</i><br>Example if you own your own domain: <i>https://virginia.birdnetpi.com</i></p>
      </td></tr></table><br>
      <table class="settingstable"><tr><td>
      <h2>Options</h2>
      <label for="silence_update_indicator">Silence Update Indicator: </label>
      <input type="checkbox" name="silence_update_indicator" <?php if($newconfig['SILENCE_UPDATE_INDICATOR'] == 1) { echo "checked"; };?> ><br>
      <p>This allows you to quiet the display of how many commits your installation is behind by relative to the Github repo. This number appears next to "Tools" when you're 50 or more commits behind.</p>

      <label for="raw_spectrogram">Minimalist Spectrograms: </label>
      <input type="checkbox" name="raw_spectrogram" <?php if($newconfig['RAW_SPECTROGRAM'] == 1) { echo "checked"; };?> ><br>
      <p>This allows you to remove the axes and labels of the spectrograms that are generated by Sox for each detection for a cleaner appearance.</p>
      </td></tr></table><br>

      <table class="settingstable"><tr><td>
      <h2>Custom Image</h2>
      <label for="custom_image">Custom Image Absolute Path: </label>
        <input name="custom_image" type="text" value="<?php print($newconfig['CUSTOM_IMAGE']);?>"/><br>

      <label for="custom_image_label">Custom Image Label: </label>
      <input name="custom_image_label" type="text" value="<?php print($newconfig['CUSTOM_IMAGE_TITLE']);?>"/><br>

      <p>These allow you to show a custom image on the Overview page of your BirdNET-Pi. This can be used to show a dynamically updating picture of your garden, for example.</p>
	  </td></tr></table><br>

      <table class="settingstable"><tr><td>
      <h2>BirdNET-Lite Settings</h2>

      <p>
        <label for="overlap">Overlap: </label>
        <input name="overlap" type="number" style="width:4em;" min="0.0" max="2.9" step="0.1" value="<?php print($newconfig['OVERLAP']);?>" required/><br>
  &nbsp;&nbsp;&nbsp;&nbsp;Min=0.0, Max=2.9
      </p>
      <p>
        <label for="confidence">Minimum Confidence: </label>
        <input name="confidence" type="number" style="width:4em;" min="0.01" max="0.99" step="0.01" value="<?php print($newconfig['CONFIDENCE']);?>" required/><br>
        &nbsp;&nbsp;&nbsp;&nbsp;Min=0.01, Max=0.99
      </p>
      <p>
        <label for="sensitivity">Sigmoid Sensitivity: </label>
        <input name="sensitivity" type="number" style="width:4em;" min="0.5" max="1.5" step="0.01" value="<?php print($newconfig['SENSITIVITY']);?>" required/><br>
  &nbsp;&nbsp;&nbsp;&nbsp;Min=0.5, Max=1.5
      </p>
      </td></tr></table><br>

      <table class="settingstable"><tr><td>
      <h2>Accessibility Settings</h2>

      <p>Birdsongs Frequency shifting configuration:<br>
        This can be useful for hearing impaired people. <br>Note: audio files will only be pitch shifted when the "FREQ SHIFT" button is manually clicked for a detection on the "Recordings" page. <br>The frequency shifting can also be activated for the realtime audio livestream, accessible in the SPECTROGRAM tab of BirdNET-Pi. Once it has been activated, it will be made available for the Live Audio feature as well.<br>Livestream is using ffmpeg for streaming its audio data, so the pitch shifter in that case will use this tool too. If you choose sox as the tool for freq shifting recorded audio files, then you must configure both sox and ffmpeg parameters: sox for recordings, and ffmpeg for livestream.<br>

        <p style="margin-left: 40px">

      <label for="freqshift_tool">Shifting tool: </label>
      <select name="freqshift_tool" class="testbtn">
            <option selected="<?php print($newconfig['FREQSHIFT_TOOL']);?>"><?php print($newconfig['FREQSHIFT_TOOL']);?></option>
      <?php
        $formats = array("sox","ffmpeg");

        $formats = array_diff($formats, array($newconfig['FREQSHIFT_TOOL']));
      foreach($formats as $format){
        echo "<option value='$format'>$format</option>";
      }
      ?>
      </select>

        Choose the shifting tool here.<br>
        </p>

        <p style="margin-left: 40px">
        Using ffmpeg:
        e.g. origin=6000, target=4000, performs a shift of 2000 Hz down.<br>
        <label for="freqshift_hi">Origin [Hz]: </label>
        <input name="freqshift_hi" type="number" style="width:5em;" min="0" max="20000" step="1" value="<?php print($newconfig['FREQSHIFT_HI']);?>" required/><br>
        <label for="freqshift_lo">Target [Hz]: </label>
        <input name="freqshift_lo" type="number" style="width:5em;" min="0" max="20000" step="1" value="<?php print($newconfig['FREQSHIFT_LO']);?>" required/>
        </p>
        <p style="margin-left: 40px">
        <label for="freqshift_reconnect_delay">Livestream reconnection delay (in ms): </label>
        <input name="freqshift_reconnect_delay" type="number" style="width:5em;" min="1000" max="10000" step="100" value="<?php print($newconfig['FREQSHIFT_RECONNECT_DELAY']);?>" required/>
        </p>

        <p style="margin-left: 40px">
        Using sox:
        e.g. shiftPitch=-1200 performs a shift of 1 octave down. This value is in 100ths of a semitone.<br>
        <label for="freqshift_pitch">Pitch shift: </label>
        <input name="freqshift_pitch" type="number" style="width:6em;" min="-4000" max="4000" step="1" value="<?php print($newconfig['FREQSHIFT_PITCH']);?>" required/><br>
        </p>
		</td></tr></table><br>

        <table class="settingstable">
            <tr>
                <td>
                    <h2>Logging</h2>
                    <div class="callout callout-warning">
                        <b>Note:</b>
                        It is recommended that the Log Level be set to <b>Error</b> on production systems to keep output
                        manageable, by only reporting errors.
                        <br>
                        Not all components support the log level option at this time.
                    </div>
                </td>
            </tr>
            <tr>
                <td>Birdnet Recording:
                    <select class="testbtn" id="LogLevel_BirdnetRecordingService" name="LogLevel_BirdnetRecordingService">
                        <option value="error" <?php echo $newconfig['LogLevel_BirdnetRecordingService'] == "error" || !array_key_exists('LogLevel_BirdnetRecordingService', $newconfig) ? "selected=''" : "" ?>>
                            Errors Only
                        </option>
                        <option value="warning" <?php echo $newconfig['LogLevel_BirdnetRecordingService'] == "warning" ? "selected=''" : "" ?>>
                            Warning
                        </option>
                        <option value="info" <?php echo $newconfig['LogLevel_BirdnetRecordingService'] == "info" ? "selected=''" : "" ?>>
                            Info
                        </option>
                        <option value="debug" <?php echo $newconfig['LogLevel_BirdnetRecordingService'] == "debug" ? "selected=''" : "" ?>>
                            Debug
                        </option>
                    </select>
                </td>
            </tr>
            <tr>
                <td>Live Audio Stream:
                    <select class="testbtn" id="LogLevel_LiveAudioStreamService" name="LogLevel_LiveAudioStreamService">
                        <option value="error" <?php echo $newconfig['LogLevel_LiveAudioStreamService'] == "error" || !array_key_exists('LogLevel_LiveAudioStreamService', $newconfig) ? "selected=''" : "" ?>>
                            Errors Only
                        </option>
                        <option value="warning" <?php echo $newconfig['LogLevel_LiveAudioStreamService'] == "warning" ? "selected=''" : "" ?>>
                            Warning
                        </option>
                        <option value="info" <?php echo $newconfig['LogLevel_LiveAudioStreamService'] == "info" ? "selected=''" : "" ?>>
                            Info
                        </option>
                        <option value="debug" <?php echo $newconfig['LogLevel_LiveAudioStreamService'] == "debug" ? "selected=''" : "" ?>>
                            Debug
                        </option>
                    </select>
                </td>
            </tr>
            <tr>
                <td>Spectrogram Service:
                    <select class="testbtn" id="LogLevel_SpectrogramViewerService" name="LogLevel_SpectrogramViewerService">
                        <option value="error" <?php echo $newconfig['LogLevel_SpectrogramViewerService'] == "error" || !array_key_exists('LogLevel_SpectrogramViewerService', $newconfig) ? "selected=''" : "" ?>>
                            Errors Only
                        </option>
                        <option value="warning" <?php echo $newconfig['LogLevel_SpectrogramViewerService'] == "warning" ? "selected=''" : "" ?>>
                            Warning
                        </option>
                        <option value="info" <?php echo $newconfig['LogLevel_SpectrogramViewerService'] == "info" ? "selected=''" : "" ?>>
                            Info
                        </option>
                        <option value="debug" <?php echo $newconfig['LogLevel_SpectrogramViewerService'] == "debug" ? "selected=''" : "" ?>>
                            Debug
                        </option>
                    </select>
                </td>
            </tr>
            <tr>
                <td>
                    <small>
                        <b>'error'</b> - Show all errors, including ones which can be recovered from. <b>This is the default value.</b><br>
                        <b>'warning'</b> - Show all warnings and errors. Any message related to possibly incorrect or unexpected events will be shown.<br>
                        <b>'info'</b> - Show informative messages and output during processing. This is in addition to warnings and errors. This will produce more output, use this for initial debugging.<br>
                        <b>'debug'</b> - Show everything, including debugging information. Produces a lot of output.<br>
                    </small>
                </td>
            </tr>
        </table>
      <br><br>
      <input type="hidden" name="view" value="Advanced">
<div class="float">
      <button type="submit" id="advancedformsubmit" onclick="collectrtspUrls(); if(document.getElementById('advancedform').checkValidity()){this.innerHTML = 'Updating... please wait.';this.classList.add('disabled')}" name="submit" value="advanced">
<?php
if(isset($_GET['submit'])){
  echo '<script>alert("Settings successfully updated");</script>';
}
echo "Update Settings";
?>
      </button></div>
      </form>
      <form action="" method="GET">
<div class="float">
        <button type="submit" name="view" value="Settings">Basic Settings</button>
</div>
      </form>
</div>
