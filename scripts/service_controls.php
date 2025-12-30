<?php
require_once "scripts/common.php";
$home = get_home();

function do_service_mount($action) {
  echo "value=\"sudo systemctl ".$action." ".get_service_mount_name()." && sudo reboot\"";
}
function service_status($name) {
  global $home;
  if($name == "birdnet_analysis.service") {
    $filesinproc=trim(shell_exec("ls ".$home."/BirdSongs/StreamData | wc -l"));
    if($filesinproc > 200) { 
       echo "<span style='color:#fc6603'>(stalled - backlog of ".$filesinproc." files in ~/BirdSongs/StreamData/)</span>";
       return;
    }
  } 
  $op = shell_exec("sudo systemctl status ".$name." | grep Active");
  if (stripos($op, " active (running)") || stripos($op, " active (mounted)")) {
      echo "<span style='color:green'>(active)</span>";
  } elseif (stripos($op, " inactive ")) {
      echo "<span style='color:#fc6603'>(inactive)</span>";
  } else {
      $status = "ERROR";
      if (preg_match("/(\S*)\s*\((\S+)\)/", $op, $matches)) {
          $status =  $matches[1]. " [" . $matches[2] . "]";
      }
      // Get full systemctl status output for error details
      $full_status = shell_exec("sudo systemctl status ".$name." 2>&1");
      $full_status = htmlspecialchars($full_status, ENT_QUOTES, 'UTF-8');
      $service_id = str_replace('.', '_', $name);
      echo "<span style='color:red;cursor:pointer;text-decoration:underline;' onclick='showErrorDetails(\"".$service_id."\")'>($status)</span>";
      echo "<div id='error_details_".$service_id."' style='display:none;'>".$full_status."</div>";
  }
}
?>
<html>
<meta name="viewport" content="width=device-width, initial-scale=1">
<br>
<div class="servicecontrols">
<form action="views.php" method="GET">
    <h3>Live Audio Stream <?php echo service_status("livestream.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop livestream.service && sudo systemctl stop icecast2.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart livestream.service && sudo systemctl restart icecast2.service">Restart </button>
    <button type="submit" name="submit" value="sudo systemctl disable --now livestream.service && sudo systemctl disable icecast2 && sudo systemctl stop icecast2.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable icecast2 && sudo systemctl start icecast2.service && sudo systemctl enable --now livestream.service">Enable</button>
  </div>
    <h3>Web Terminal <?php echo service_status("web_terminal.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop web_terminal.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart web_terminal.service">Restart </button>
    <button type="submit" name="submit" value="sudo systemctl disable --now web_terminal.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now web_terminal.service">Enable</button>
  </div>
    <h3>BirdNET Log <?php echo service_status("birdnet_log.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop birdnet_log.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart birdnet_log.service">Restart </button>
    <button type="submit" name="submit" value="sudo systemctl disable --now birdnet_log.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now birdnet_log.service">Enable</button>
  </div>
    <h3>BirdNET Analysis <?php echo service_status("birdnet_analysis.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop birdnet_analysis.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart birdnet_analysis.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now birdnet_analysis.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now birdnet_analysis.service">Enable</button>
  </div>
    <h3>Streamlit Statistics <?php echo service_status("birdnet_stats.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop birdnet_stats.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart birdnet_stats.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now birdnet_stats.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now birdnet_stats.service">Enable</button>
  </div>
    <h3>Recording Service <?php echo service_status("birdnet_recording.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop birdnet_recording.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart birdnet_recording.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now birdnet_recording.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now birdnet_recording.service">Enable</button>
  </div>
    <h3>Chart Viewer <?php echo service_status("chart_viewer.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop chart_viewer.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart chart_viewer.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now chart_viewer.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now chart_viewer.service">Enable</button>
  </div>
    <h3>Spectrogram Viewer <?php echo service_status("spectrogram_viewer.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop spectrogram_viewer.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart spectrogram_viewer.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now spectrogram_viewer.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now spectrogram_viewer.service">Enable</button>
  </div>
    <h3>TFT Display <?php echo service_status("tft_display.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop tft_display.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart tft_display.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now tft_display.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now tft_display.service">Enable</button>
  </div>
    <h3>Ram drive (!experimental!) <?php echo service_status(get_service_mount_name());?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" <?php do_service_mount("disable");?> onclick="return confirm('This will reboot, are you sure?')">Disable</button>
    <button type="submit" name="submit" <?php do_service_mount("enable");?> onclick="return confirm('This will reboot, are you sure?')">Enable</button>
  </div>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="stop_core_services.sh">Stop Core Services</button>
  </div>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="restart_services.sh">Restart Core Services</button>
  </div>
</form>
</div>

<!-- Modal for Error Details -->
<div id="errorModal" class="modal">
  <div class="modal-content">
    <h2>Service Error Details</h2>
    <pre id="errorDetailsContent" style="text-align:left;background-color:black;color:white;padding:15px;overflow-x:auto;max-height:400px;overflow-y:auto;"></pre>
    <div style="margin-top:15px;">
      <button onclick="copyErrorDetails()" style="background-color: rgb(219, 255, 235);padding: 12px;">Copy to Clipboard</button>
      <button onclick="closeErrorModal()" style="background-color: rgb(219, 255, 235);padding: 12px;">Close</button>
    </div>
  </div>
</div>

<script>
function showErrorDetails(serviceId) {
  var errorDetails = document.getElementById('error_details_' + serviceId).textContent;
  document.getElementById('errorDetailsContent').textContent = errorDetails;
  document.getElementById('errorModal').style.display = 'block';
}

function closeErrorModal() {
  document.getElementById('errorModal').style.display = 'none';
}

function copyErrorDetails() {
  var errorText = document.getElementById('errorDetailsContent').textContent;
  
  // Try modern Clipboard API first (more secure and recommended)
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(errorText).then(function() {
      alert('Error details copied to clipboard!');
    }).catch(function(err) {
      // Fallback to deprecated method if modern API fails
      copyErrorDetailsFallback(errorText);
    });
  } else {
    // Fallback for older browsers
    copyErrorDetailsFallback(errorText);
  }
}

function copyErrorDetailsFallback(text) {
  // Create a temporary textarea element
  var textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  
  // Select and copy the text
  textarea.select();
  textarea.setSelectionRange(0, 99999); // For mobile devices
  
  try {
    document.execCommand('copy');
    alert('Error details copied to clipboard!');
  } catch (err) {
    alert('Failed to copy error details. Please select and copy manually.');
  }
  
  document.body.removeChild(textarea);
}

// Close modal when clicking outside of it
window.onclick = function(event) {
  var modal = document.getElementById('errorModal');
  if (event.target == modal) {
    closeErrorModal();
  }
}
</script>
