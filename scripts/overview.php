<?php
error_reporting(E_ERROR);
ini_set('display_errors',1);
ini_set('session.gc_maxlifetime', 7200);
session_set_cookie_params(7200);
session_start();
require_once 'scripts/common.php';
$home = get_home();
$config = get_config();

set_timezone();
$myDate = date('Y-m-d');
$chart = "Combo-$myDate.png";

$db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
$db->busyTimeout(1000);

if(isset($_GET['custom_image'])){
  if(isset($config["CUSTOM_IMAGE"])) {
  ?>
    <br>
    <h3><?php echo $config["CUSTOM_IMAGE_TITLE"]; ?></h3>
    <?php
    $image_data = file_get_contents($config["CUSTOM_IMAGE"]);
    $image_base64 = base64_encode($image_data);
    $img_tag = "<img src='data:image/png;base64," . $image_base64 . "'>";
    echo $img_tag;
  }
  die();
}

if(isset($_GET['clearcache'])) {
  unset($_SESSION['images']);
  header("Location: overview.php");
  die();
}

if(isset($_GET['blacklistimage'])) {
  ensure_authenticated('You must be authenticated.');
  $imageid = $_GET['blacklistimage'];
  $file_handle = fopen($home."/BirdNET-Pi/scripts/blacklisted_images.txt", 'a+');
  fwrite($file_handle, $imageid . "\n");
  fclose($file_handle);
  unset($_SESSION['images']);
  die("OK");
}

if(isset($_GET['fetch_chart_string']) && $_GET['fetch_chart_string'] == "true") {
  $myDate = date('Y-m-d');
  $chart = "Combo-$myDate.png";
  echo $chart;
  die();
}

if(isset($_GET['ajax_chart_data']) && $_GET['ajax_chart_data'] == "true") {
  header('Content-Type: application/json');

  // Species aggregate: name, count, max confidence
  $stmt1 = $db->prepare("SELECT Com_Name, Sci_Name, COUNT(*) as cnt, MAX(Confidence) as maxConf FROM detections WHERE Date = DATE('now','localtime') GROUP BY Sci_Name ORDER BY cnt DESC");
  ensure_db_ok($stmt1);
  $res1 = $stmt1->execute();
    // For image fetching
    $image_provider = null;
    $fallback_provider = null;
    if (!empty($config["IMAGE_PROVIDER"])) {
      $flickr = new Flickr();
      $wikipedia = new Wikipedia();
      if ($config["IMAGE_PROVIDER"] === 'FLICKR') {
          $image_provider = $flickr;
          $fallback_provider = $wikipedia;
      } else {
          $image_provider = $wikipedia;
          $fallback_provider = $flickr;
      }
    }

    $species = [];
    while ($row = $res1->fetchArray(SQLITE3_ASSOC)) {
      $img_url = "";
      if ($image_provider) {
        if (!isset($_SESSION['species_portal_v12_cache'])) {
          $_SESSION['species_portal_v12_cache'] = [];
        }
        $search_name = trim($row['Com_Name']);
        $key = array_search($search_name, array_column($_SESSION['species_portal_v12_cache'], 0));
        
        if ($key !== false) {
          $img_url = $_SESSION['species_portal_v12_cache'][$key][1];
        } else {
          $cached_image = $image_provider->get_image($row['Sci_Name'], $fallback_provider);
          if ($cached_image && !empty($cached_image["image_url"])) {
            $image_data = array($search_name, $cached_image["image_url"], $cached_image["title"], $cached_image["photos_url"], $cached_image["author_url"], $cached_image["license_url"]);
            array_push($_SESSION["species_portal_v12_cache"], $image_data);
            $img_url = $cached_image["image_url"];
          } else {
            $image_data = array($search_name, "", "Not Found", "", "", "");
            array_push($_SESSION["species_portal_v12_cache"], $image_data);
          }
        }
      }

      $species[] = [
        'name' => $row['Com_Name'],
        'sciName' => $row['Sci_Name'],
        'count' => (int)$row['cnt'],
        'maxConf' => round((float)$row['maxConf'], 3),
        'image' => $img_url
      ];
    }

  // Hourly breakdown per species
  $stmt2 = $db->prepare("SELECT Com_Name, CAST(strftime('%H', Time) AS INTEGER) as hour, COUNT(*) as cnt FROM detections WHERE Date = DATE('now','localtime') GROUP BY Com_Name, hour");
  ensure_db_ok($stmt2);
  $res2 = $stmt2->execute();
  $hourly = [];
  while ($row = $res2->fetchArray(SQLITE3_ASSOC)) {
    $name = $row['Com_Name'];
    if (!isset($hourly[$name])) $hourly[$name] = [];
    $hourly[$name][(int)$row['hour']] = (int)$row['cnt'];
  }
  // Weather breakdown per hour
  $weather = [];
  $check_table = $db->query("SELECT name FROM sqlite_master WHERE type='table' AND name='weather'");
  if ($check_table && $check_table->fetchArray()) {
      $stmt3 = $db->prepare("SELECT Hour, Temp, ConditionCode FROM weather WHERE Date = DATE('now','localtime')");
      if ($stmt3) {
          $res3 = $stmt3->execute();
          while ($row = $res3->fetchArray(SQLITE3_ASSOC)) {
              $weather[(int)$row['Hour']] = [
                  'temp' => round((float)$row['Temp']),
                  'code' => (int)$row['ConditionCode']
              ];
          }
      }
  }

  echo json_encode(['species' => $species, 'hourly' => $hourly, 'weather' => $weather, 'currentHour' => (int)date('G')]);
  die();
}

if(isset($_GET['ajax_detections']) && $_GET['ajax_detections'] == "true" && isset($_GET['previous_detection_identifier'])) {

  $statement4 = $db->prepare('SELECT Com_Name, Sci_Name, Date, Time, Confidence, File_Name FROM detections ORDER BY Date DESC, Time DESC LIMIT 15');
  ensure_db_ok($statement4);
  $result4 = $statement4->execute();
  if(!isset($_SESSION['images'])) {
    $_SESSION['images'] = [];
  }
  $iterations = 0;
  $image_provider = null;

  // hopefully one of the 5 most recent detections has an image that is valid, we'll use that one as the most recent detection until the newer ones get their images created
  while($mostrecent = $result4->fetchArray(SQLITE3_ASSOC)) {
    $comname = preg_replace('/ /', '_', $mostrecent['Com_Name']);
    $sciname = preg_replace('/ /', '_', $mostrecent['Sci_Name']);
    $comnamegraph = str_replace("'", "\'", $mostrecent['Com_Name']);
    $comname = preg_replace('/\'/', '', $comname);
    $filename = "By_Date/".$mostrecent['Date']."/".$comname."/".$mostrecent['File_Name'];

    // check to make sure the image actually exists, sometimes it takes a minute to be created\
    if(file_exists($home."/BirdSongs/Extracted/".$filename.".png")){
      if($_GET['previous_detection_identifier'] == $filename) { die(); }
      if($_GET['only_name'] == "true") { echo $comname.",".$filename;die(); }

      $iterations++;

      if (!empty($config["IMAGE_PROVIDER"])) {
        if ($image_provider === null) {
          $flickr = new Flickr();
          $wikipedia = new Wikipedia();
          if ($config["IMAGE_PROVIDER"] === 'FLICKR') {
              $image_provider = $flickr;
              $fallback_provider = $wikipedia;
          } else {
              $image_provider = $wikipedia;
              $fallback_provider = $flickr;
          }
          if ($image_provider->is_reset()) {
            $_SESSION['images'] = [];
          }
        }

        if (!isset($_SESSION['species_portal_v12_cache'])) {
          $_SESSION['species_portal_v12_cache'] = [];
        }
        
        $search_name = trim($mostrecent['Com_Name']);
        $key = array_search($search_name, array_column($_SESSION['species_portal_v12_cache'], 0));
        
        if ($key !== false) {
          $image = $_SESSION['species_portal_v12_cache'][$key];
        } else {
          $cached_image = $image_provider->get_image($mostrecent['Sci_Name'], $fallback_provider);
          if ($cached_image && !empty($cached_image["image_url"])) {
            $image_data = array($search_name, $cached_image["image_url"], $cached_image["title"], $cached_image["photos_url"], $cached_image["author_url"], $cached_image["license_url"]);
            array_push($_SESSION["species_portal_v12_cache"], $image_data);
            $image = $image_data;
          } else {
            $image_data = array($search_name, "", "Not Found", "", "", "");
            array_push($_SESSION["species_portal_v12_cache"], $image_data);
            $image = $image_data;
          }
        }
      }
    ?>
        <style>
        .fade-in {
          opacity: 1;
          animation-name: fadeInOpacity;
          animation-iteration-count: 1;
          animation-timing-function: ease-in;
          animation-duration: 1s;
        }

        @keyframes fadeInOpacity {
          0% {
            opacity: 0;
          }
          100% {
            opacity: 1;
          }
        }
        </style>
        <table class="<?php echo ($_GET['previous_detection_identifier'] == 'undefined') ? '' : 'fade-in';  ?>">
          <h3>Most Recent Detection: <span style="font-weight: normal;"><?php echo $mostrecent['Date']." ".$mostrecent['Time'];?></span></h3>
          <tr>
            <td class="relative"><a target="_blank" href="index.php?filename=<?php echo $mostrecent['File_Name']; ?>"><img class="copyimage" title="Open in new tab" width="25" height="25" src="images/copy.png"></a>
            <div class="centered_image_container" style="margin-bottom: 0px !important;">
              <?php if(!empty($config["IMAGE_PROVIDER"]) && !empty($image[1])) { ?>
                <img style="object-fit: contain; background: #f8fafc; border-radius: 8px;" onerror="this.style.display='none'" onclick='setModalText(<?php echo $iterations; ?>,"<?php echo urlencode($image[2]); ?>", "<?php echo $image[3]; ?>", "<?php echo $image[4]; ?>", "<?php echo $image[1]; ?>", "<?php echo $image[5]; ?>")' src="<?php echo $image[1]; ?>" class="img1">
              <?php } ?>
              <form action="" method="GET">
                  <input type="hidden" name="view" value="Species Stats">
                  <button type="submit" name="species" value="<?php echo $mostrecent['Com_Name'];?>"><?php echo $mostrecent['Com_Name'];?></button>
                  <br>
                  <i><?php echo $mostrecent['Sci_Name'];?></i>
                  <a href="<?php $info_url = get_info_url($mostrecent['Sci_Name']); $url = $info_url['URL']; echo $url ?>" target="_blank">
                  <img style="width: unset !important; display: inline; height: 1em; cursor: pointer;" title="Info" src="images/info.png" width="25"></a>
                  <a href="https://wikipedia.org/wiki/<?php echo $sciname;?>" target="_blank"><img style="width: unset !important; display: inline; height: 1em; cursor: pointer;" title="Wikipedia" src="images/wiki.png" width="25"></a>
                  <img style="width: unset !important;display: inline;height: 1em;cursor:pointer" title="View species stats" onclick="generateMiniGraph(this, '<?php echo $comnamegraph; ?>')" width=25 src="images/chart.svg">
                  <br>Confidence: <?php echo $percent = round((float)round($mostrecent['Confidence'],2) * 100 ) . '%';?><br></div><br>
                  <div class='custom-audio-player' data-audio-src="<?php echo $filename; ?>" data-image-src="<?php echo $filename.".png";?>"></div>
                  </td></form>
          </tr>
        </table> <?php break;
      }
  }
  if($iterations == 0) {
    $statement2 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Date == DATE(\'now\', \'localtime\')');
    ensure_db_ok($statement2);
    $result2 = $statement2->execute();
    $todaycount = $result2->fetchArray(SQLITE3_ASSOC);
    if($todaycount['COUNT(*)'] > 0) {
      echo "<h3>Your system is currently processing a backlog of audio. This can take several hours before normal functionality of your BirdNET-Pi resumes.</h3>";
    } else {
      echo "<h3>No Detections For Today.</h3>";
    }
  }
  die();
}

if(isset($_GET['ajax_left_chart']) && $_GET['ajax_left_chart'] == "true") {

  // Retrieve the cached data from session without regenerating
  $chart_data = get_summary();
  $_SESSION['chart_data'] = $chart_data;
?>
<div class="kpi-cards" style="justify-content: center; margin: 0; max-width: 100%;">
  <div class="kpi-card">
    <div class="kpi-icon">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
    </div>
    <div class="kpi-value"><?php echo number_format($chart_data['totalcount']);?></div>
    <div class="kpi-label">Total Detections</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon kpi-icon-today">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
    </div>
    <div class="kpi-value"><form action="" method="GET" style="display:inline"><button type="submit" name="view" value="Todays Detections" class="kpi-link"><?php echo number_format($chart_data['todaycount']);?></button></form></div>
    <div class="kpi-label">Today</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon kpi-icon-hour">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    </div>
    <div class="kpi-value"><?php echo number_format($chart_data['hourcount']);?></div>
    <div class="kpi-label">Last Hour</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon kpi-icon-species">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
    </div>
    <div class="kpi-value"><form action="" method="GET" style="display:inline"><input type="hidden" name="view" value="Recordings"><button type="submit" name="date" value="<?php echo date('Y-m-d');?>" class="kpi-link"><?php echo $chart_data['speciestally'];?></button></form></div>
    <div class="kpi-label">Species Today</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon kpi-icon-total-species">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
    </div>
    <div class="kpi-value"><form action="" method="GET" style="display:inline"><button type="submit" name="view" value="Species Stats" class="kpi-link"><?php echo $chart_data['totalspeciestally'];?></button></form></div>
    <div class="kpi-label">Total Species</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-icon" style="background: #fff7ed; color: #f97316;">
      ✨
    </div>
    <div class="kpi-value"><?php echo $chart_data['newspeciestally'];?></div>
    <div class="kpi-label">New Species Today</div>
  </div>
  <?php if(!empty($chart_data['topspecies'])) { ?>
  <div class="kpi-card kpi-card-highlight">
    <div class="kpi-icon kpi-icon-top">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
    </div>
    <div class="kpi-value"><?php echo htmlspecialchars($chart_data['topspecies']);?></div>
    <div class="kpi-label">Top Species (<?php echo $chart_data['topspeciescount'];?>x)</div>
  </div>
  <?php } ?>
</div>
<?php
  die();
}

if(isset($_GET['ajax_center_chart']) && $_GET['ajax_center_chart'] == "true") {

  // Retrieve the cached data from session without regenerating
  $chart_data = $_SESSION['chart_data'];
?>
<div class="kpi-cards kpi-cards-compact" style="justify-content: center; margin: 0; max-width: 100%;">
  <div class="kpi-card kpi-card-sm"><div class="kpi-value"><?php echo number_format($chart_data['totalcount']);?></div><div class="kpi-label">Total</div></div>
  <div class="kpi-card kpi-card-sm"><div class="kpi-value"><form action="" method="GET" style="display:inline"><button type="submit" name="view" value="Todays Detections" class="kpi-link"><?php echo number_format($chart_data['todaycount']);?></button></form></div><div class="kpi-label">Today</div></div>
  <div class="kpi-card kpi-card-sm"><div class="kpi-value"><?php echo number_format($chart_data['hourcount']);?></div><div class="kpi-label">Last Hour</div></div>
  <div class="kpi-card kpi-card-sm"><div class="kpi-value"><form action="" method="GET" style="display:inline"><button type="submit" name="view" value="Species Stats" class="kpi-link"><?php echo $chart_data['totalspeciestally'];?></button></form></div><div class="kpi-label">Species Total</div></div>
  <div class="kpi-card kpi-card-sm"><div class="kpi-value"><form action="" method="GET" style="display:inline"><input type="hidden" name="view" value="Recordings"><button type="submit" name="date" value="<?php echo date('Y-m-d');?>" class="kpi-link"><?php echo $chart_data['speciestally'];?></button></form></div><div class="kpi-label">Species Today</div></div>
  <div class="kpi-card kpi-card-sm"><div class="kpi-value"><?php echo $chart_data['newspeciestally'];?></div><div class="kpi-label">New Today</div></div>
  <?php if(!empty($chart_data['topspecies'])) { ?>
  <div class="kpi-card kpi-card-sm kpi-card-highlight"><div class="kpi-value" style="font-size:0.95em"><?php echo htmlspecialchars($chart_data['topspecies']);?></div><div class="kpi-label">Top (<?php echo $chart_data['topspeciescount'];?>x)</div></div>
  <?php } ?>
</div>

<?php
  die();
}

if (get_included_files()[0] === __FILE__) {
  echo '<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Overview</title>
</head>';
}
?>
<div class="overview">
  <dialog style="margin-top: 5px;max-height: 95vh;
  overflow-y: auto;overscroll-behavior:contain" id="attribution-dialog">
    <h1 id="modalHeading"></h1>
    <p id="modalText"></p>
    <button onclick="hideDialog()">Close</button>
    <button style="font-weight:bold;color:blue" onclick="if(confirm('Are you sure you want to blacklist this image?')) { blacklistImage(); }" <?php if($config["IMAGE_PROVIDER"] === 'WIKIPEDIA'){ echo 'hidden';} ?> >Blacklist this image</button>
  </dialog>
  <script src="static/dialog-polyfill.js"></script>
  <script src="static/Chart.bundle.js"></script>
  <script src="static/chartjs-plugin-trendline.min.js"></script>
  <script>
  var last_photo_link;
  var dialog = document.querySelector('dialog');
  dialogPolyfill.registerDialog(dialog);

  function showDialog() {
    document.getElementById('attribution-dialog').showModal();
  }

  function hideDialog() {
    document.getElementById('attribution-dialog').close();
  }

  function blacklistImage() {
    const match = last_photo_link.match(/\d+$/); // match one or more digits
    const result = match ? match[0] : null; // extract the first match or return null if no match is found
    console.log(last_photo_link)
    const xhttp = new XMLHttpRequest();
    xhttp.onload = function() {
      if(this.responseText.length > 0) {
       location.reload();
      }
    }
    xhttp.open("GET", "overview.php?blacklistimage="+result, true);
    xhttp.send();

  }

  function shorten(u) {
    if (u.length < 48) {
      return u;
    }
    uend = u.slice(u.length - 16);
    ustart = u.substr(0, 32);
    var shorter = ustart + '...' + uend;
    return shorter;
  }

  function setModalText(iter, title, text, authorlink, photolink, licenseurl) {
    let text_display = shorten(text);
    let authorlink_display = shorten(authorlink);
    let licenseurl_display = shorten(licenseurl);
    document.getElementById('modalHeading').innerHTML = "Photo: \""+decodeURIComponent(title.replaceAll("+"," "))+"\" Attribution";
    document.getElementById('modalText').innerHTML = "<div><img style='border-radius:5px;max-height: calc(100vh - 15rem);display: block;margin: 0 auto;' src='"+photolink+"'></div><br><div style='white-space:nowrap'>Image link: <a target='_blank' href="+text+">"+text_display+"</a><br>Author link: <a target='_blank' href="+authorlink+">"+authorlink_display+"</a><br>License URL: <a href="+licenseurl+" target='_blank'>"+licenseurl_display+"</a></div>";
    last_photo_link = text;
    showDialog();
  }
  </script>  
<div class="overview-stats">
<div class="right-column">
<div class="left-column" style="flex: unset; padding-left: 0; margin-bottom: 8px;"></div>
<div class="center-column">
</div>
<?php
// New/Rare species lists removed for KPI redesign
?>
<div class="chart-container" style="max-width: 100%;">
  <div class="chart-canvas-wrapper" style="max-width: 100%; margin:8px auto 0;overflow:hidden;">
    <canvas id="hourlyHeatmap"></canvas>
  </div>
</div>
<?php
$refresh = $config['RECORDING_LENGTH'];
$dividedrefresh = $refresh/4;
if($dividedrefresh < 1) { 
  $dividedrefresh = 1;
}
?>

<div id="most_recent_detection"></div>
<h3>5 Most Recent Detections</h3>
<div style="padding-bottom:8px;" id="detections_table"><h3>Loading...</h3></div>

<h3>Currently Analyzing</h3>
<?php
$refresh = $config['RECORDING_LENGTH'];
$time = time();
echo "<img id=\"spectrogramimage\" style=\"max-height:200px;width:auto;\" src=\"spectrogram.png?nocache=$time\">";

?>

<div id="customimage"></div>
<br>

</div>



</div>
</div>
<script>
// we're passing a unique ID of the currently displayed detection to our script, which checks the database to see if the newest detection entry is that ID, or not. If the IDs don't match, it must mean we have a new detection and it's loaded onto the page
function loadDetectionIfNewExists(previous_detection_identifier=undefined) {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    // if there's a new detection that needs to be updated to the page
    if(this.responseText.length > 0 && !this.responseText.includes("Database is busy") && !this.responseText.includes("No Detections") || previous_detection_identifier == undefined) {
      document.getElementById("most_recent_detection").innerHTML = this.responseText;

      // only going to load left chart & 5 most recents if there's a new detection
      loadLeftChart();
      loadFiveMostRecentDetections();
      refreshTopTen();

      // Now that new HTML is inserted, re-run player init:
      initCustomAudioPlayers();
    }
  }
  xhttp.open("GET", "overview.php?ajax_detections=true&previous_detection_identifier="+previous_detection_identifier, true);
  xhttp.send();
}
function loadLeftChart() {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    if(this.responseText.length > 0 && !this.responseText.includes("Database is busy")) {
      document.getElementsByClassName("left-column")[0].innerHTML = this.responseText;
      loadCenterChart();
    }
  }
  xhttp.open("GET", "overview.php?ajax_left_chart=true", true);
  xhttp.send();
}
function loadCenterChart() {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    if(this.responseText.length > 0 && !this.responseText.includes("Database is busy")) {
      document.getElementsByClassName("center-column")[0].innerHTML = this.responseText;
    }
  }
  xhttp.open("GET", "overview.php?ajax_center_chart=true", true);
  xhttp.send();
}
function refreshTopTen() {
  if (window.DashboardCharts) {
    DashboardCharts.refresh();
  }
}
function refreshDetection() {
  if (!document.hidden) {
    const audioPlayers = document.querySelectorAll(".custom-audio-player");
    // If no custom-audio-player elements are found, refresh
    if (audioPlayers.length === 0) {
      loadDetectionIfNewExists();
      return;
    }
    // Check if any custom audio player is currently playing
    let isPlaying = false;
    audioPlayers.forEach((player) => {
      const audioEl = player.querySelector("audio");
      if (audioEl && audioEl.currentTime > 0 && !audioEl.paused && !audioEl.ended && audioEl.readyState > 2) {
        isPlaying = true;
      }
    });
    // If none are playing, refresh detections
    if (!isPlaying) {
      const currentIdentifier = audioPlayers[0]?.dataset.audioSrc || undefined;
      loadDetectionIfNewExists(currentIdentifier);
    }
  }
}
function loadFiveMostRecentDetections() {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    if(this.responseText.length > 0 && !this.responseText.includes("Database is busy")) {
      document.getElementById("detections_table").innerHTML= this.responseText;
    }
  }
  if (window.innerWidth > 500) {
    xhttp.open("GET", "todays_detections.php?ajax_detections=true&display_limit=undefined&hard_limit=5", true);
  } else {
    xhttp.open("GET", "todays_detections.php?ajax_detections=true&display_limit=undefined&hard_limit=5&mobile=true", true);
  }
  xhttp.send();
}
function refreshCustomImage(){
  // Find the customimage element
  var customimage = document.getElementById("customimage");

  function updateCustomImage() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "overview.php?custom_image=true", true);
    xhr.onload = function() {
      customimage.innerHTML = xhr.responseText;
    }
    xhr.send();
  }
  updateCustomImage();
}
function startAutoRefresh() {
    i_fn1 = window.setInterval(function(){
                    document.getElementById("spectrogramimage").src = "spectrogram.png?nocache="+Date.now();
                    }, <?php echo $refresh; ?>*1000);
    i_fn2 = window.setInterval(refreshDetection, <?php echo intval($dividedrefresh); ?>*1000);
    if (customImage) i_fn3 = window.setInterval(refreshCustomImage, 1000);
}
<?php if(isset($config["CUSTOM_IMAGE"]) && strlen($config["CUSTOM_IMAGE"]) > 2){?>
customImage = true;
<?php } else { ?>
customImage = false;
<?php } ?>
window.addEventListener("load", function(){
  loadDetectionIfNewExists();
});
document.addEventListener("visibilitychange", function() {
  console.log(document.visibilityState);
  console.log(document.hidden);
  if (document.hidden) {
    clearInterval(i_fn1);
    clearInterval(i_fn2);
    if (customImage) clearInterval(i_fn3);
  } else {
    loadDetectionIfNewExists();
    startAutoRefresh();
  }
});
startAutoRefresh();
</script>

<style>
  .tooltip {
  background-color: rgba(15, 23, 42, 0.9);
  color: white;
  border-radius: 8px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  padding: 8px 12px;
  font-size: 0.85em;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  transition: opacity 0.2s ease-in-out;
}
</style>
<script src="static/custom-audio-player.js"></script>
<script src="static/generateMiniGraph.js"></script>
<script src="static/dashboard-charts.js?v=5"></script>
<script>if(window.DashboardCharts){DashboardCharts.refresh();}</script>
<script>
// Listen for the scroll event on the window object
window.addEventListener('scroll', function() {
  // Get all chart elements
  var charts = document.querySelectorAll('.chartdiv');
  
  // Loop through all chart elements and remove them
  charts.forEach(function(chart) {
    chart.parentNode.removeChild(chart);
    window.chartWindow = undefined;
  });
});

</script>
