<?php

/* Prevent XSS input */
$_GET   = filter_input_array(INPUT_GET, FILTER_SANITIZE_STRING);
$_POST  = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);

ini_set('user_agent', 'PHP_ImageProvider/1.0');
error_reporting(E_ERROR);
ini_set('display_errors', 0);
require_once 'scripts/common.php';
$home = get_home();
$config = get_config();
$image_provider_name = strtolower($config["IMAGE_PROVIDER"] ?? 'wikipedia');

$result = fetch_species_array($_GET['sort']);

if(!file_exists($home."/BirdNET-Pi/scripts/disk_check_exclude.txt") || strpos(file_get_contents($home."/BirdNET-Pi/scripts/disk_check_exclude.txt"),"##start") === false) {
  file_put_contents($home."/BirdNET-Pi/scripts/disk_check_exclude.txt", "");
  file_put_contents($home."/BirdNET-Pi/scripts/disk_check_exclude.txt", "##start\n##end\n");
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

<div class="stats">
<div class="column">
<div style="width: auto;
   text-align: center">
   <form action="views.php" method="GET">
    <input type="hidden" name="sort" value="<?php if(isset($_GET['sort'])){echo $_GET['sort'];}?>">
      <input type="hidden" name="view" value="Species Stats">
      <button <?php if(!isset($_GET['sort']) || $_GET['sort'] == "alphabetical"){ echo "class='sortbutton active'";} else { echo "class='sortbutton'"; }?> type="submit" name="sort" value="alphabetical">
         <img src="images/sort_abc.svg" title="Sort by alphabetical" alt="Sort by alphabetical">
      </button>
      <button <?php if(isset($_GET['sort']) && $_GET['sort'] == "occurrences"){ echo "class='sortbutton active'";} else { echo "class='sortbutton'"; }?> type="submit" name="sort" value="occurrences">
         <img src="images/sort_occ.svg" title="Sort by occurrences" alt="Sort by occurrences">
      </button>
      <button <?php if(isset($_GET['sort']) && $_GET['sort'] == "confidence"){ echo "class='sortbutton active'";} else { echo "class='sortbutton'"; }?> type="submit" name="sort" value="confidence">
         <img src="images/sort_conf.svg" title="Sort by confidence" alt="Sort by confidence">
      </button>
      <button <?php if(isset($_GET['sort']) && $_GET['sort'] == "date"){ echo "class='sortbutton active'";} else { echo "class='sortbutton'"; }?> type="submit" name="sort" value="date">
         <img src="images/sort_date.svg" title="Sort by date" alt="Sort by date">
      </button>
   </form>
</div>
<br>
<form action="views.php" method="GET">
<input type="hidden" name="sort" value="<?php if(isset($_GET['sort'])){echo $_GET['sort'];}?>">
<input type="hidden" name="view" value="Species Stats">
<table>
  <?php
  $birds = array();
  $values = array();

  while($results=$result->fetchArray(SQLITE3_ASSOC))
  {
    $comname = preg_replace('/ /', '_', $results['Com_Name']);
    $comname = preg_replace('/\'/', '', $comname);
    $filename = "/By_Date/".$results['Date']."/".$comname."/".$results['File_Name'];
    $birds[] = $results['Com_Name'];
    $values[] = get_label($results, $_GET['sort']);
  }

  if(count($birds) > 45) {
    $num_cols = 3;
  } else {
    $num_cols = 1;
  }
  $num_rows = ceil(count($birds) / $num_cols);

  for ($row = 0; $row < $num_rows; $row++) {
    echo "<tr>";

    for ($col = 0; $col < $num_cols; $col++) {
      $index = $row + $col * $num_rows;

      if ($index < count($birds)) {
        ?>
        <td>
            <button type="submit" name="species" value="<?php echo $birds[$index];?>"><?php echo $values[$index];?></button>
        </td>
        <?php
      } else {
        echo "<td></td>";
      }
    }

    echo "</tr>";
  }
  ?>
</table>
</form>
</div>
<dialog style="margin-top: 5px;max-height: 95vh;
  overflow-y: auto;overscroll-behavior:contain" id="attribution-dialog">
  <h1 id="modalHeading"></h1>
  <p id="modalText"></p>
  <button onclick="hideDialog()">Close</button>
</dialog>
<script src="static/dialog-polyfill.js"></script>
<script>
var dialog = document.querySelector('dialog');
dialogPolyfill.registerDialog(dialog);

function showDialog() {
  document.getElementById('attribution-dialog').showModal();
}

function hideDialog() {
  document.getElementById('attribution-dialog').close();
}

function setModalText(iter, title, text, authorlink) {
  document.getElementById('modalHeading').innerHTML = "Photo "+iter+": \""+title+"\" Attribution";
  document.getElementById('modalText').innerHTML = "<div style='white-space:nowrap'>Image link: <a target='_blank' href="+text+">"+text+"</a><br>Author link: <a target='_blank' href="+authorlink+">"+authorlink+"</a></div>";
  showDialog();
}
</script>  
<div class="column center">
<?php if(!isset($_GET['species'])){
?><p class="centered">Choose a species to load images from <?php echo ucfirst($image_provider_name); ?>.</p>
<?php
};?>
<?php if(isset($_GET['species'])){
  $species = $_GET['species'];
  $iter=0;
<<<<<<< HEAD
  $config = get_config();
  $result3 = fetch_best_detection(htmlspecialchars_decode($_GET['species'], ENT_QUOTES));
=======
>>>>>>> 9a4d0c72 (Fix notification tests by creating config and updating expectations)
while($results=$result3->fetchArray(SQLITE3_ASSOC)){
  $count = $results['COUNT(*)'];
  $maxconf = round((float)round($results['MAX(Confidence)'],2) * 100 ) . '%';
  $date = $results['Date'];
  $time = $results['Time'];
  $name = $results['Com_Name'];
  $sciname = $results['Sci_Name'];
  $dbsciname = preg_replace('/ /', '_', $sciname);
  $comname = preg_replace('/ /', '_', $results['Com_Name']);
  $comname = preg_replace('/\'/', '', $comname);
  $linkname = preg_replace('/_/', '+', $dbsciname);
  $filename = "/By_Date/".$date."/".$comname."/".$results['File_Name'];
  $engname = get_com_en_name($sciname);

  $info_url = get_info_url($results['Sci_Name']);
  $url = $info_url['URL'];
  $url_title = $info_url['TITLE'];
  echo str_pad("<h3>$species</h3>
    <table><tr>
  <td class=\"relative\"><a target=\"_blank\" href=\"index.php?filename=".$results['File_Name']."\"><img title=\"Open in new tab\" class=\"copyimage\" width=25 src=\"images/copy.png\"></a><i>$sciname</i>
  <a href=\"$url\" target=\"_blank\"><img style=\"width: unset !important; display: inline; height: 1em; cursor: pointer;\" title=\"$url_title\" src=\"images/info.png\" width=\"20\"></a>
  <a href=\"https://wikipedia.org/wiki/$sciname\" target=\"_blank\"><img style=\"width: unset !important; display: inline; height: 1em; cursor: pointer;\" title=\"Wikipedia\" src=\"images/wiki.png\" width=\"20\"></a><br>
  Occurrences: $count<br>
  Max Confidence: $maxconf<br>
  Best Recording: $date $time<br><br>
  <video onplay='setLiveStreamVolume(0)' onended='setLiveStreamVolume(1)' onpause='setLiveStreamVolume(1)' controls poster=\"$filename.png\" title=\"$filename\"><source src=\"$filename\"></video></td>
  </tr>
    </table>
  <p>Loading Images from ".ucfirst($image_provider_name)."</p>", '6096');
  
  echo "<script>document.getElementsByTagName(\"h3\")[0].scrollIntoView();</script>";
  
  ob_flush();
  flush();

  if ($image_provider_name === 'flickr' && ! empty($config["FLICKR_API_KEY"])) {
    $flickrjson = json_decode(file_get_contents("https://www.flickr.com/services/rest/?method=flickr.photos.search&api_key=".$config["FLICKR_API_KEY"]."&text=\"".str_replace(' ', '%20', $engname)."\"&license=2%2C3%2C4%2C5%2C6%2C9&sort=relevance&per_page=15&format=json&nojsoncallback=1"), true)["photos"]["photo"];

    foreach ($flickrjson as $val) {

      $iter++;
      $modaltext = "https://flickr.com/photos/".$val["owner"]."/".$val["id"];
      $authorlink = "https://flickr.com/people/".$val["owner"];
      $imageurl = 'https://farm' .$val["farm"]. '.static.flickr.com/' .$val["server"]. '/' .$val["id"]. '_'  .$val["secret"].  '.jpg';
      echo "<span style='cursor:pointer;' onclick='setModalText(".$iter.",\"".$val["title"]."\",\"".$modaltext."\", \"".$authorlink."\")'><img style='vertical-align:top' src=\"$imageurl\"></span>"; 
    }
  } elseif ($image_provider_name === 'wikipedia') {
    $wiki = new Wikipedia();
    $cache = $wiki->get_image($sciname);
    if (!empty($cache['image_url'])) {
      echo "<span><img style='vertical-align:top' src=\"".$cache['image_url']."\"></span>";
    }
  }
}
}
?>
<?php if(isset($_GET['species'])){?>
<br><br>
<div class="brbanner">Best Recordings for Other Species:</div><br>
<?php } else {?>
<hr><br>
<?php } ?>
  <form action="views.php" method="GET">
    <input type="hidden" name="sort" value="<?php if(isset($_GET['sort'])){echo $_GET['sort'];}?>">
    <input type="hidden" name="view" value="Species Stats">
    <table>
<?php
$excludelines = [];
while($results=$result->fetchArray(SQLITE3_ASSOC))
{
$comname = preg_replace('/ /', '_', $results['Com_Name']);
$comname = preg_replace('/\'/', '', $comname);
$filename = "/By_Date/".$results['Date']."/".$comname."/".$results['File_Name'];

array_push($excludelines, $results['Date']."/".$comname."/".$results['File_Name']);
array_push($excludelines, $results['Date']."/".$comname."/".$results['File_Name'].".png");
?>
      <tr>
      <td class="relative"><a target="_blank" href="index.php?filename=<?php echo $results['File_Name']; ?>"><img title="Open in new tab" class="copyimage" width=25 src="images/copy.png"></a>
        <button type="submit" name="species" value="<?php echo $results['Com_Name'];?>"><?php echo $results['Com_Name'];?></button><br><b>Occurrences:</b> <?php echo $results['Count'];?><br>
      <b>Max Confidence:</b> <?php echo $percent = round((float)round($results['MaxConfidence'],2) * 100 ) . '%';?><br>
      <b>Best Recording:</b> <?php echo $results['Date']." ".$results['Time'];?><br><video onplay='setLiveStreamVolume(0)' onended='setLiveStreamVolume(1)' onpause='setLiveStreamVolume(1)' controls poster="<?php echo $filename.".png";?>" preload="none" title="<?php echo $filename;?>"><source src="<?php echo $filename;?>" type="audio/mp3"></video></td>
      </tr>
<?php
}

$file = file_get_contents($home."/BirdNET-Pi/scripts/disk_check_exclude.txt");
file_put_contents($home."/BirdNET-Pi/scripts/disk_check_exclude.txt", "##start"."\n".implode("\n",$excludelines)."\n".substr($file, strpos($file, "##end")));
?>
    </table>
  </form>
</div>
</div>
<?php
if (get_included_files()[0] === __FILE__) {
  echo '</body></html>';
}
