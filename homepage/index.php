<?php

$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if (strpos($requestUri, '/api/v1/') === 0) {
  include_once 'scripts/api.php';
  die();
}

/* Prevent XSS input */
$_GET   = filter_input_array(INPUT_GET, FILTER_SANITIZE_STRING);
$_POST  = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);
require_once 'scripts/common.php';
$config = get_config();
$site_name = get_sitename();
$color_scheme = get_color_scheme();
set_timezone();

?>
<!DOCTYPE html>
<html lang="en">
<head>
<title><?php echo $site_name; ?></title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="BirdNET-Pi - Bird sound identification and monitoring dashboard">
<link id="iconLink" rel="shortcut icon" sizes=85x85 href="images/bird.png" />
<link rel="stylesheet" href="<?php echo $color_scheme . '?v=' . date('n.d.y', filemtime($color_scheme)); ?>">
<link rel="stylesheet" type="text/css" href="static/dialog-polyfill.css" />
</head>
<body>
<div class="banner">
  <div class="logo" style="display: none;">
<?php if(isset($_GET['logo'])) {
echo "<a href=\"https://github.com/zach7036/BirdNET-Pi.git\" target=\"_blank\"><img style=\"width:40px;height:40px;\" src=\"images/bird.png\"></a>";
} else {
echo "<a href=\"https://github.com/zach7036/BirdNET-Pi.git\" target=\"_blank\"><img style=\"width:40px;height:40px;\" src=\"images/bird.png\"></a>";
}?>
  </div>

  <div class="stream">
<?php
if(isset($_GET['stream'])){
  ensure_authenticated('You cannot listen to the live audio stream');
      echo "
  <audio id=\"live-audio-player\" controls autoplay><source src=\"/stream\"></audio>
  <script>
    if (window.history.replaceState) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  </script>
  <h1 style=\"display: none;\"><a href=\"/\"><img class=\"topimage\" src=\"images/bnp.png\"></a></h1>
  </div>";
} else {
    echo "
  <div class=\"stream\">
  <form action=\"index.php\" method=\"GET\">
    <!-- Live Audio button moved to sidebar, original form kept for logical routing if needed -->
    <button type=\"submit\" name=\"stream\" value=\"play\">🎙️ Live Audio</button>
  </form>
  <h1 style=\"display: none;\"><a href=\"/\"><img class=\"topimage\" src=\"images/bnp.png\"></a></h1>
  </div>";
}
?>
</div>
<?php
if(isset($_GET['filename'])) {
  $filename = $_GET['filename'];
echo "
<iframe src=\"views.php?view=Recordings&filename=$filename\" allow=\"autoplay\"></iframe>";
} else {
  echo "
<iframe src=\"views.php\" allow=\"autoplay\"></iframe>";
}
