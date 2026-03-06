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

<?php
if(isset($_GET['stream'])){
  ensure_authenticated('You cannot listen to the live audio stream');
  echo "<div style=\"position: fixed; top: 12px; right: 20px; z-index: 999999;\">
          <audio id=\"live-audio-player\" controls autoplay><source src=\"/stream\"></audio>
        </div>";
  echo "<script>
          if (window.history.replaceState) {
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        </script>";
} else {
  // Replaced the fragile .banner layout with a direct, viewport-anchored float
  echo "<form action=\"index.php\" method=\"GET\" style=\"position: fixed; top: 12px; right: 20px; z-index: 999999; margin: 0; padding: 0;\">
          <button type=\"submit\" name=\"stream\" value=\"play\" style=\"padding: 8px 16px; border-radius: 8px; background: var(--bg-card, #fff); color: var(--text-primary, #333); border: 1px solid var(--border, #ccc); box-shadow: 0 4px 6px rgba(0,0,0,0.15); font-weight: bold; cursor: pointer;\">🎙️ Live Audio</button>
        </form>";
}
?>

<?php
if(isset($_GET['filename'])) {
  $filename = $_GET['filename'];
echo "
<iframe src=\"views.php?view=Recordings&filename=$filename\" allow=\"autoplay\" style=\"position: fixed; top: 0; left: 0; width: 100%; height: 100%; border: none; z-index: 1;\"></iframe>";
} else {
  echo "
<iframe src=\"views.php\" allow=\"autoplay\" style=\"position: fixed; top: 0; left: 0; width: 100%; height: 100%; border: none; z-index: 1;\"></iframe>";
}
?>
