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
      echo "<span style='color:red'>($status)</span>";
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
    <h3>Timer Service <?php echo service_status("birdnet_timer.service");?></h3>
  <div role="group" class="btn-group-center">
    <button type="submit" name="submit" value="sudo systemctl stop birdnet_timer.service">Stop</button>
    <button type="submit" name="submit" value="sudo systemctl restart birdnet_timer.service">Restart</button>
    <button type="submit" name="submit" value="sudo systemctl disable --now birdnet_timer.service">Disable</button>
    <button type="submit" name="submit" value="sudo systemctl enable --now birdnet_timer.service">Enable</button>
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
