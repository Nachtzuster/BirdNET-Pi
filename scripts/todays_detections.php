<?php

/* Prevent XSS input */
$_GET   = filter_input_array(INPUT_GET, FILTER_SANITIZE_STRING);
$_POST  = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);

ini_set('session.gc_maxlifetime', 7200);
ini_set('user_agent', 'PHP_Flickr/1.0');
session_set_cookie_params(7200);
session_start();
error_reporting(E_ERROR);
ini_set('display_errors',1);
require_once 'scripts/common.php';
$home = get_home();
$config = get_config();
$site_name = get_sitename();
set_timezone();

if(isset($kiosk) && $kiosk == true) {
    echo "<div style='margin-top:20px' class=\"centered\"><h1><a><img class=\"topimage\" src=\"images/bnp.png\"></a></h1></div>
</div><div class=\"centered\"><h3>$site_name</h3></div><hr>";
} else {
  $kiosk = false;
}

$db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
$db->busyTimeout(1000);

$statement1 = $db->prepare('SELECT COUNT(*) FROM detections');
ensure_db_ok($statement1);
$result1 = $statement1->execute();
$totalcount = $result1->fetchArray(SQLITE3_ASSOC);

$statement2 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Date == DATE(\'now\', \'localtime\')');
ensure_db_ok($statement2);
$result2 = $statement2->execute();
$todaycount = $result2->fetchArray(SQLITE3_ASSOC);

$statement3 = $db->prepare('SELECT COUNT(*) FROM detections WHERE Date == Date(\'now\', \'localtime\') AND TIME >= TIME(\'now\', \'localtime\', \'-1 hour\')');
ensure_db_ok($statement3);
$result3 = $statement3->execute();
$hourcount = $result3->fetchArray(SQLITE3_ASSOC);

$statement4 = $db->prepare('SELECT Com_Name, Sci_Name, Time, Confidence FROM detections LIMIT 1');
ensure_db_ok($statement4);
$result4 = $statement4->execute();
$mostrecent = $result4->fetchArray(SQLITE3_ASSOC);

$statement5 = $db->prepare('SELECT COUNT(DISTINCT(Com_Name)) FROM detections WHERE Date == Date(\'now\', \'localtime\')');
ensure_db_ok($statement5);
$result5 = $statement5->execute();
$todayspeciestally = $result5->fetchArray(SQLITE3_ASSOC);

$statement6 = $db->prepare('SELECT COUNT(DISTINCT(Com_Name)) FROM detections');
ensure_db_ok($statement6);
$result6 = $statement6->execute();
$totalspeciestally = $result6->fetchArray(SQLITE3_ASSOC);

if(isset($_GET['comname'])) {
 $birdName = $_GET['comname'];
 $birdName = str_replace("_", " ", $birdName);


// Prepare a SQL statement to retrieve the detection data for the specified bird
$stmt = $db->prepare('SELECT Date, COUNT(*) AS Detections FROM detections WHERE Com_Name = :com_name AND Date BETWEEN DATE("now", "-30 days") AND DATE("now") GROUP BY Date');

// Bind the bird name parameter to the SQL statement
$stmt->bindValue(':com_name', $birdName);

// Execute the SQL statement and get the result set
$result = $stmt->execute();

// Fetch the result set as an associative array
$data = array();
while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
  $data[$row['Date']] = $row['Detections'];
}

// Create an array of all dates in the last 14 days
$last14Days = array();
for ($i = 0; $i < 31; $i++) {
  $last14Days[] = date('Y-m-d', strtotime("-$i days"));
}

// Merge the data array with the last14Days array
$data = array_merge(array_fill_keys($last14Days, 0), $data);

// Sort the data by date in ascending order
ksort($data);

// Convert the data to an array of objects
$data = array_map(function($date, $count) {
  return array('date' => $date, 'count' => $count);
}, array_keys($data), $data);

// Close the database connection
$db->close();

// Return the data as JSON
echo json_encode($data);
die();

}

// from https://stackoverflow.com/questions/2690504/php-producing-relative-date-time-from-timestamps
function relativeTime($ts)
{
    if(!ctype_digit($ts))
        $ts = strtotime($ts);

    $diff = time() - $ts;
    if($diff == 0)
        return 'now';
    elseif($diff > 0)
    {
        $day_diff = floor($diff / 86400);
        if($day_diff == 0)
        {
            if($diff < 60) return 'just now';
            if($diff < 120) return '1 minute ago';
            if($diff < 3600) return floor($diff / 60) . ' minutes ago';
            if($diff < 7200) return '1 hour ago';
            if($diff < 86400) return floor($diff / 3600) . ' hours ago';
        }
        if($day_diff == 1) return 'Yesterday';
        if($day_diff < 7) return $day_diff . ' days ago';
        if($day_diff < 31) return ceil($day_diff / 7) . ' weeks ago';
        if($day_diff < 60) return 'last month';
        return date('F Y', $ts);
    }
    else
    {
        $diff = abs($diff);
        $day_diff = floor($diff / 86400);
        if($day_diff == 0)
        {
            if($diff < 120) return 'in a minute';
            if($diff < 3600) return 'in ' . floor($diff / 60) . ' minutes';
            if($diff < 7200) return 'in an hour';
            if($diff < 86400) return 'in ' . floor($diff / 3600) . ' hours';
        }
        if($day_diff == 1) return 'Tomorrow';
        if($day_diff < 4) return date('l', $ts);
        if($day_diff < 7 + (7 - date('w'))) return 'next week';
        if(ceil($day_diff / 7) < 4) return 'in ' . ceil($day_diff / 7) . ' weeks';
        if(date('n', $ts) == date('n') + 1) return 'next month';
        return date('F Y', $ts);
    }
}


if(isset($_GET['ajax_detections']) && $_GET['ajax_detections'] == "true"  ) {
  if(isset($_GET['searchterm'])) {
    if(strtolower(explode(" ", $_GET['searchterm'])[0]) == "not") {
      $not = "NOT ";
      $operator = "AND";
      $_GET['searchterm'] =  str_replace("not ", "", $_GET['searchterm']);
      $_GET['searchterm'] =  str_replace("NOT ", "", $_GET['searchterm']);
    } else {
      $not = "";
      $operator = "OR";
    }
    $searchquery = "AND (Com_name ".$not."LIKE '%".$_GET['searchterm']."%' ".$operator." Sci_name ".$not."LIKE '%".$_GET['searchterm']."%' ".$operator." Confidence ".$not."LIKE '%".$_GET['searchterm']."%' ".$operator." File_Name ".$not."LIKE '%".$_GET['searchterm']."%' ".$operator." Time ".$not."LIKE '%".$_GET['searchterm']."%')";
  } else {
    $searchquery = "";
  }
  if(isset($_GET['display_limit']) && is_numeric($_GET['display_limit'])){
    $statement0 = $db->prepare('SELECT Date, Time, Com_Name, Sci_Name, Confidence, File_Name FROM detections WHERE Date == Date(\'now\', \'localtime\') '.$searchquery.' ORDER BY Time DESC LIMIT '.(intval($_GET['display_limit'])-40).',40');
  } else {
    // legacy mode
    if(isset($_GET['hard_limit']) && is_numeric($_GET['hard_limit'])) {
      $statement0 = $db->prepare('SELECT Date, Time, Com_Name, Sci_Name, Confidence, File_Name FROM detections WHERE Date == Date(\'now\', \'localtime\') '.$searchquery.' ORDER BY Time DESC LIMIT '.$_GET['hard_limit']);
    } else {
      $statement0 = $db->prepare('SELECT Date, Time, Com_Name, Sci_Name, Confidence, File_Name FROM detections WHERE Date == Date(\'now\', \'localtime\') '.$searchquery.' ORDER BY Time DESC');
    }
    
  }
  ensure_db_ok($statement0);
  $result0 = $statement0->execute();

  ?> <table>
   <?php

  if(!isset($_SESSION['images'])) {
    $_SESSION['images'] = [];
  }
  $iterations = 0;
  $flickr = null;

  while($todaytable=$result0->fetchArray(SQLITE3_ASSOC))
  {
    $iterations++;

    $comname = preg_replace('/ /', '_', $todaytable['Com_Name']);
    $comname = preg_replace('/\'/', '', $comname);
    $filename = "/By_Date/".date('Y-m-d')."/".$comname."/".$todaytable['File_Name'];
    $filename_formatted = $todaytable['Date']."/".$comname."/".$todaytable['File_Name'];
    $sciname = preg_replace('/ /', '_', $todaytable['Sci_Name']);
    $engname = get_com_en_name($todaytable['Sci_Name']);
    $engname_url = str_replace("'", '', str_replace(' ', '_', $engname));

    $info_url = get_info_url($todaytable['Sci_Name']);
    $url = $info_url['URL'];
    $url_title = $info_url['TITLE'];

    if (!empty($config["FLICKR_API_KEY"]) && (isset($_GET['display_limit']) || isset($_GET['hard_limit']) || $_GET['kiosk'] == true) ) {
      if ($flickr === null) {
        $flickr = new Flickr();
      }
      if (isset($_SESSION["FLICKR_FILTER_EMAIL"]) && $_SESSION["FLICKR_FILTER_EMAIL"] !== $flickr->get_uid_from_db()['uid']) {
        unset($_SESSION['images']);
        $_SESSION["FLICKR_FILTER_EMAIL"] = $flickr->get_uid_from_db()['uid'];
      }

      // if we already searched flickr for this species before, use the previous image rather than doing an unneccesary api call
      $key = array_search($comname, array_column($_SESSION['images'], 0));
      if ($key !== false) {
        $image = $_SESSION['images'][$key];
      } else {
        $flickr_cache = $flickr->get_image($todaytable['Sci_Name']);
        array_push($_SESSION["images"], array($comname, $flickr_cache["image_url"], $flickr_cache["title"], $flickr_cache["photos_url"], $flickr_cache["author_url"], $flickr_cache["license_url"]));
        $image = $_SESSION['images'][count($_SESSION['images']) - 1];
      }
    }
  ?>
        <?php if(isset($_GET['display_limit']) && is_numeric($_GET['display_limit'])){ ?>
          <tr class="relative" id="<?php echo $iterations; ?>">
          <td class="relative">
            <img style='cursor:pointer;right:45px' src='images/delete.svg' onclick='deleteDetection("<?php echo $filename_formatted; ?>")' class="copyimage" width=25 title='Delete Detection'>
            <a target="_blank" href="index.php?filename=<?php echo $todaytable['File_Name']; ?>"><img class="copyimage" title="Open in new tab" width=25 src="images/copy.png"></a>
        
            
          <div class="centered_image_container">
            <?php if(!empty($config["FLICKR_API_KEY"]) && strlen($image[2]) > 0) { ?>
              <img onclick='setModalText(<?php echo $iterations; ?>,"<?php echo urlencode($image[2]); ?>", "<?php echo $image[3]; ?>", "<?php echo $image[4]; ?>", "<?php echo $image[1]; ?>", "<?php echo $image[5]; ?>")' src="<?php echo $image[1]; ?>" class="img1">
            <?php } ?>

            <?php echo $todaytable['Time'];?><br>   
          <b><a class="a2" href="<?php echo $url;?>" target="top"><?php echo $todaytable['Com_Name'];?></a></b><br>
          <i><?php echo $todaytable['Sci_Name'];?></i>
          <a href="<?php echo $url;?>" target="_blank"><img style="cursor:pointer;float:unset;display:inline" title=<?php echo $url_title;?> src="images/info.png" width="20"></a>
          <a href="https://wikipedia.org/wiki/<?php echo $sciname;?>" target="_blank"><img style=";cursor:pointer;float:unset;display:inline" title="Wikipedia" src="images/wiki.png" width="20"></a>
          <img style=";cursor:pointer;float:unset;display:inline" title="View species stats" onclick="generateMiniGraph(this, '<?php echo $comname; ?>')" width=20 src="images/chart.svg"><br>
          <b>Confidence:</b> <?php echo round((float)round($todaytable['Confidence'],2) * 100 ) . '%';?><br></div><br>
          <video onplay='setLiveStreamVolume(0)' onended='setLiveStreamVolume(1)' onpause='setLiveStreamVolume(1)' controls poster="<?php echo $filename.".png";?>" preload="none" title="<?php echo $filename;?>"><source preload="none" src="<?php echo $filename;?>"></video>
          </td>
        <?php } else { //legacy mode ?>
          <tr class="relative" id="<?php echo $iterations; ?>">
          <td><?php if($_GET['kiosk'] == true) { echo relativeTime(strtotime($todaytable['Time'])); } else {echo $todaytable['Time'];}?><br></td>
          <td id="recent_detection_middle_td">
          <div>
            <div>
            <?php if(!empty($config["FLICKR_API_KEY"]) && (isset($_GET['hard_limit']) || $_GET['kiosk'] == true) && strlen($image[2]) > 0) { ?>
              <img style="float:left;height:75px;" onclick='setModalText(<?php echo $iterations; ?>,"<?php echo urlencode($image[2]); ?>", "<?php echo $image[3]; ?>", "<?php echo $image[4]; ?>", "<?php echo $image[1]; ?>", "<?php echo $image[5]; ?>")' src="<?php echo $image[1]; ?>" id="birdimage" class="img1">
            <?php } ?>
          </div>
            <div>
            <form action="" method="GET">
                    <input type="hidden" name="view" value="Species Stats">
		    <button class="a2" type="submit" name="species" value="<?php echo $todaytable['Com_Name'];?>"><?php echo $todaytable['Com_Name'];?></button>
	            <br><i>
		    <?php echo $todaytable['Sci_Name'];?>
	                <br>
	                    <a href="<?php echo $url;?>" target="_blank"><img style="height: 1em;cursor:pointer;float:unset;display:inline" title=<?php echo $url_title;?> src="images/info.png" width="25"></a>
			    <?php if($_GET['kiosk'] == false){?>
	    		    <a href="https://wikipedia.org/wiki/<?php echo $sciname;?>" target="_blank"><img style="height: 1em;cursor:pointer;float:unset;display:inline" title="Wikipedia" src="images/wiki.png" width="25"></a>
	                    <img style="height: 1em;cursor:pointer;float:unset;display:inline" title="View species stats" onclick="generateMiniGraph(this, '<?php echo $comname; ?>')" width=25 src="images/chart.svg">
	                    <a target="_blank" href="index.php?filename=<?php echo $todaytable['File_Name']; ?>"><img style="height: 1em;cursor:pointer;float:unset;display:inline" class="copyimage-mobile" title="Open in new tab" width=16 src="images/copy.png"></a>
		    	    <?php } ?></i>
	                <br>
	            </div>
            </form>
          </div>
          </td>
          <td><?php if(!isset($_GET['mobile'])) { echo '<b>Confidence:</b>';} echo round((float)round($todaytable['Confidence'],2) * 100 ) . '%';?><br></td>
          <?php if(!isset($_GET['mobile'])) { ?>
              <td style="min-width:180px"><audio controls preload="none" src="<?php echo $filename;?>"></audio></td>
          <?php } ?>
        <?php } ?>
  <?php }?>
        </tr>
      </table>

  <?php 
  if($iterations == 0) {
    echo "<h3>No Detections For Today.</h3>";
  }
  
  // don't show the button if there's no more detections to be displayed, we're at the end of the list
  if($iterations >= 40 && isset($_GET['display_limit']) && is_numeric($_GET['display_limit'])) { ?>
  <center>
  <button class="loadmore" onclick="loadDetections(<?php echo $_GET['display_limit'] + 40; ?>, this);" value="Today's Detections">Load 40 More...</button>
  </center>
  <?php }

  die();
}

if(isset($_GET['today_stats'])) {
  ?>
  <table>
      <tr>
  <th>Total</th>
  <th>Today</th>
  <th>Last Hour</th>
  <th>Unique Species Total</th>
  <th>Unique Species Today</th>
      </tr>
      <tr>
      <td><?php echo $totalcount['COUNT(*)'];?></td>
      <form action="" method="GET">
      <td><input type="hidden" name="view" value="Recordings"><?php if($kiosk == false){?><button type="submit" name="date" value="<?php echo date('Y-m-d');?>"><?php echo $todaycount['COUNT(*)'];?></button><?php } else { echo $todaycount['COUNT(*)']; }?></td>
      </form>
      <td><?php echo $hourcount['COUNT(*)'];?></td>
      <form action="" method="GET">
      <td><?php if($kiosk == false){?><button type="submit" name="view" value="Species Stats"><?php echo $totalspeciestally['COUNT(DISTINCT(Com_Name))'];?></button><?php }else { echo $totalspeciestally['COUNT(DISTINCT(Com_Name))']; }?></td>
      </form>
      <form action="" method="GET">
      <td><input type="hidden" name="view" value="Recordings"><?php if($kiosk == false){?><button type="submit" name="date" value="<?php echo date('Y-m-d');?>"><?php echo $todayspeciestally['COUNT(DISTINCT(Com_Name))'];?></button><?php } else { echo $todayspeciestally['COUNT(DISTINCT(Com_Name))']; }?></td>
      </form>
      </tr>
    </table>
<?php   
die(); 
}

if (get_included_files()[0] === __FILE__) {
  echo '<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BirdNET-Pi DB</title>
</head>';
}
?>
<div class="viewdb">
  <dialog style="margin-top: 5px;max-height: 95vh;
  overflow-y: auto;overscroll-behavior:contain" id="attribution-dialog">
    <h1 id="modalHeading"></h1>
    <p id="modalText"></p>
    <button style="font-weight:bold;color:blue" onclick="hideDialog()">Close</button>
    <button style="font-weight:bold;color:blue" onclick="if(confirm('Are you sure you want to blacklist this image?')) { blacklistImage(); }">Blacklist this image</button>
  </dialog>
  <script src="static/dialog-polyfill.js"></script>
  <script src="static/Chart.bundle.js"></script>
  <script src="static/chartjs-plugin-trendline.min.js"></script>
  
  <script>
    function deleteDetection(filename,copylink=false) {
    if (confirm("Are you sure you want to delete this detection from the database?") == true) {
      const xhttp = new XMLHttpRequest();
      xhttp.onload = function() {
        if(this.responseText == "OK"){
          if(copylink == true) {
            window.top.close();
          } else {
            location.reload();
          }
        } else {
          alert("Database busy.")
        }
      }
      xhttp.open("GET", "play.php?deletefile="+filename, true);
      xhttp.send();
    }
  }

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

  function setModalText(iter, title, text, authorlink, photolink, licenseurl) {
    document.getElementById('modalHeading').innerHTML = "Photo: \""+decodeURIComponent(title.replaceAll("+"," "))+"\" Attribution";
    <?php if($kiosk == false) { ?>
      document.getElementById('modalText').innerHTML = "<div><img style='border-radius:5px;max-height: calc(100vh - 15rem);display: block;margin: 0 auto;' src='"+photolink+"'></div><br><div style='white-space:nowrap'>Image link: <a target='_blank' href="+text+">"+text+"</a><br>Author link: <a target='_blank' href="+authorlink+">"+authorlink+"</a><br>License URL: <a href="+licenseurl+" target='_blank'>"+licenseurl+"</a></div>";
    <?php } else { ?>
      document.getElementById('modalText').innerHTML = "<div><img style='border-radius:5px;max-height: calc(100vh - 15rem);display: block;margin: 0 auto;' src='"+photolink+"'></div><br><div style='white-space:nowrap'>Image link: <a target='_blank'>"+text+"</a><br>Author link: <a target='_blank'>"+authorlink+"</a><br>License URL: <a target='_blank'>"+licenseurl+"</a></div>";
    <?php } ?>
    last_photo_link = text;
    showDialog();
  }
  </script>  
    <h3>Number of Detections</h3>
    <div id="todaystats" class="overview"><form action="views.php" method="GET"><table>
      <tr>
  <th>Total</th>
  <th>Today</th>
  <th>Last Hour</th>
  <th>Unique Species Total</th>
  <th>Unique Species Today</th>
      </tr>
      <tr>
      <td><?php echo $totalcount['COUNT(*)'];?></td>
      <td><input type="hidden" name="view" value="Recordings"><?php if($kiosk == false){?><button type="submit" name="date" value="<?php echo date('Y-m-d');?>"><?php echo $todaycount['COUNT(*)'];?></button><?php } else { echo $todaycount['COUNT(*)']; }?></td>
      <td><?php echo $hourcount['COUNT(*)'];?></td>
      <td><?php if($kiosk == false){?><button type="submit" name="view" value="Species Stats"><?php echo $totalspeciestally['COUNT(DISTINCT(Com_Name))'];?></button><?php }else { echo $totalspeciestally['COUNT(DISTINCT(Com_Name))']; }?></td>
      <td><input type="hidden" name="view" value="Recordings"><?php if($kiosk == false){?><button type="submit" name="date" value="<?php echo date('Y-m-d');?>"><?php echo $todayspeciestally['COUNT(DISTINCT(Com_Name))'];?></button><?php } else { echo $todayspeciestally['COUNT(DISTINCT(Com_Name))']; }?></td>
      </tr>
    </table></form></div>


    <h3>Today's Detections <?php if($kiosk == false) { ?>— <input autocomplete="off" size="18" type="text" placeholder="Search..." id="searchterm" name="searchterm"><?php } ?></h3>

    <div style="padding-bottom:10px" id="detections_table"><h3>Loading...</h3></div>

    <?php if($kiosk == false) { ?>
    <button onclick="switchViews(this);" class="legacyview">Legacy view</button>
    <?php } ?>

</div>

<?php if($kiosk == true) { ?>
  <script>
    const scrollToTop = () => {
  const c = document.documentElement.scrollTop || document.body.scrollTop;
  if (c > 0) {
    window.requestAnimationFrame(scrollToTop);
    window.scrollTo(0, c - c / 8);
  }
};
</script>
<button onclick="scrollToTop();" style="background-color: #dbffeb;padding: 20px;position: fixed;bottom: 5%;right: 5%;transition:box-shadow 280ms cubic-bezier(0.4, 0, 0.2, 1);box-shadow:0px 3px 1px -2px rgb(0 0 0 / 20%), 0px 2px 2px 0px rgb(0 0 0 / 14%), 0px 1px 5px 0px rgb(0 0 0 / 12%);">Scroll To Top</button>
<?php } ?>

<script>

var timer = '';
searchterm = "";

<?php if($kiosk == false) { ?>
document.getElementById("searchterm").onkeydown = (function(e) {
  if (e.key === "Enter") {
      clearTimeout(timer);
      searchDetections(document.getElementById("searchterm").value);
      document.getElementById("searchterm").blur();
  } else {
     /*
     clearTimeout(timer);
     timer = setTimeout(function() {
        searchDetections(document.getElementById("searchterm").value);

        setTimeout(function() {
            // search auto submitted and now the user is probably scrolling, get the keyboard out of the way & prevent browser from jumping to the top when a video is played
            document.getElementById("searchterm").blur();
        }, 2000);
     }, 1000);
     */
  }
});
<?php } ?>

function switchViews(element) {
  if(searchterm == ""){
    document.getElementById("detections_table").innerHTML = "<h3>Loading <?php echo $todaycount['COUNT(*)']; ?> detections...</h3>";
  } else {
    document.getElementById("detections_table").innerHTML = "<h3>Loading...</h3>";
  }
  if(element.innerHTML == "Legacy view") {
    element.innerHTML = "Normal view";
    loadDetections(undefined);
  } else if(element.innerHTML == "Normal view") {
    element.innerHTML = "Legacy view";
    loadDetections(40);
  }
}
function searchDetections(searchvalue) {
    document.getElementById("detections_table").innerHTML = "<h3>Loading...</h3>";
    searchterm = searchvalue;
    if(document.getElementsByClassName('legacyview')[0].innerHTML == "Normal view") {
      loadDetections(undefined,undefined);  
    } else {
      loadDetections(40,undefined);
    }
}
function loadDetections(detections_limit, element=undefined) {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    <?php if($kiosk == false) { ?>
      document.getElementsByClassName("legacyview")[0].style.display="unset";
    <?php } ?>
    if(typeof element !== "undefined")
    {
     element.remove();
     document.getElementById("detections_table").innerHTML+= this.responseText;
    } else {
     document.getElementById("detections_table").innerHTML= this.responseText;
    }
    
  }
  if(searchterm != ""){
    xhttp.open("GET", "todays_detections.php?ajax_detections=true&display_limit="+detections_limit+"&searchterm="+searchterm, true);
  } else {
    <?php if($kiosk == true) { ?>
      xhttp.open("GET", "todays_detections.php?ajax_detections=true&display_limit="+detections_limit+"&kiosk=true", true);
    <?php } else { ?>
      xhttp.open("GET", "todays_detections.php?ajax_detections=true&display_limit="+detections_limit, true);
    <?php } ?>
  }
  xhttp.send();
}
function refreshTodayStats() {
  const xhttp = new XMLHttpRequest();
  xhttp.onload = function() {
    if(this.responseText.length > 0 && !this.responseText.includes("Database is busy")) {
      document.getElementById("todaystats").innerHTML = this.responseText;
    }
  }
  xhttp.open("GET", "todays_detections.php?today_stats=true", true);
  xhttp.send();
}
window.addEventListener("load", function(){
  <?php if($kiosk == true) { ?>
    document.getElementById("myTopnav").remove();
    loadDetections(undefined);
    refreshTodayStats();
    // refresh the kiosk detection list every minute
    setTimeout(function() {
        loadDetections(undefined);
        refreshTodayStats();
    }, 60000);
  <?php } else { ?>
    loadDetections(40);
  <?php } ?>
});
</script>

<style>
  .tooltip {
  background-color: white;
  border: 1px solid #ccc;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
  padding: 10px;
  transition: opacity 0.2s ease-in-out;
}
</style>

<script>
function generateMiniGraph(elem, comname) {
  // Make an AJAX call to fetch the number of detections for the bird species
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/todays_detections.php?comname=' + comname);
  xhr.onload = function() {
    if (xhr.status === 200) {
      var detections = JSON.parse(xhr.responseText);

      // Create a div element for the chart window
      if (typeof(window.chartWindow) != 'undefined') {
        document.body.removeChild(window.chartWindow);
        window.chartWindow = undefined;
      }
      var chartWindow = document.createElement('div');
      chartWindow.className = "chartdiv"
      document.body.appendChild(chartWindow);


            // Create a canvas element for the chart
      var canvas = document.createElement('canvas');
      canvas.width = chartWindow.offsetWidth;
      canvas.height = chartWindow.offsetHeight;
      chartWindow.appendChild(canvas);

      // Create a new Chart.js chart
      var ctx = canvas.getContext('2d');
      var chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: detections.map(item => item.date),
          datasets: [{
            label: 'Detections',
            data: detections.map(item => item.count),
            backgroundColor: '#9fe29b',
            borderColor: '#77c487',
            borderWidth: 1,
            lineTension: 0.3, // Add smoothing to the line
            pointRadius: 1, // Make the data points smaller
            pointHitRadius: 10, // Increase the area around data points for mouse events

          trendlineLinear: {
            style: "rgba(55, 99, 64, 0.5)",
            lineStyle: "solid",
            width: 1.5
          }

          }]
        },
        options: {
          layout: {
            padding: {
              right: 10
            }
          },
          title: {
            display: true,
            text: 'Detections Over 30d'
          },
          legend: {
            display: false
          },
          scales: {
            xAxes: [{
              display: false,
              gridLines: {
                display: false // Hide the gridlines on the x-axis
              },
              ticks: {
                autoSkip: true,
                maxTicksLimit: 2
              }
            }],
            yAxes: [{
              gridLines: {
                display: false // Hide the gridlines on the y-axis
              },
              ticks: {
                beginAtZero: true,
                precision: 0,
                stepSize: 1
              }
            }]
          }
        }
      });

      // Position the chart window to the right of the button
      var buttonRect = elem.getBoundingClientRect();
      var chartRect = chartWindow.getBoundingClientRect();
      if (window.innerWidth < 700) {
        chartWindow.style.left = 'calc(75% - ' + (chartRect.width / 2) + 'px)';
      } else {
        chartWindow.style.left = (buttonRect.right + 10) + 'px';
      }

      // Calculate the top position of the chart to center it with the button
      var buttonCenter = buttonRect.top + (buttonRect.height / 2);
      var chartHeight = chartWindow.offsetHeight;
      var chartTop = buttonCenter - (chartHeight / 2);
      chartWindow.style.top = chartTop + 'px';

      // Add a close button to the chart window
      var closeButton = document.createElement('button');
      closeButton.id = "chartcb";
      closeButton.innerText = 'X';
      closeButton.style.position = 'absolute';
      closeButton.style.top = '5px';
      closeButton.style.right = '5px';
      closeButton.addEventListener('click', function() {
        document.body.removeChild(chartWindow);
        window.chartWindow = undefined;
      });
      chartWindow.appendChild(closeButton);
      window.chartWindow = chartWindow;
    }
  };
  xhr.send();
}

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
