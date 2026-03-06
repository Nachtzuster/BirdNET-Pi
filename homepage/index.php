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


<style>
  #live-audio-panel {
    position: fixed;
    top: 0;
    right: calc(100vw - 100%); /* Dynamically sits flush with scrollbar if present, or right edge if not */
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 999999;
    display: flex;
    align-items: flex-start;
    pointer-events: none; /* Let clicks pass through when hidden */
  }
  #live-audio-panel.open {
    transform: translateX(0);
    pointer-events: auto;
  }
  #live-audio-tab {
    position: absolute;
    left: -65px;
    width: 65px;
    height: 30px; /* Force tab to be vertically smaller as requested */
    top: 0;
    background: var(--bg-card, #fff);
    border: 1px solid var(--border, #ccc);
    border-top: none;
    border-right: none;
    border-radius: 0 0 0 8px;
    box-shadow: -2px 2px 6px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.85em;
    font-weight: bold;
    color: var(--text-primary, #333);
    user-select: none;
    pointer-events: auto; /* Tab always clickable */
  }
  #live-audio-tab:hover {
    background: var(--bg-button-hover, #f1f5f9);
  }
  #live-audio-content {
    background: var(--bg-card, #fff);
    border: 1px solid var(--border, #ccc);
    border-top: none;
    border-right: none;
    border-radius: 0 0 0 8px;
    box-shadow: -4px 4px 12px rgba(0,0,0,0.15);
    padding: 2px 10px;
    display: flex;
    align-items: center;
    visibility: hidden;
    opacity: 0;
    transition: opacity 0.3s ease, visibility 0.3s;
  }
  #live-audio-panel.open #live-audio-content {
    visibility: visible;
    opacity: 1;
  }
  #live-audio-player {
    height: 36px;
    outline: none;
  }
</style>
<div id="live-audio-panel" onmouseleave="startCloseTimer()" onmouseenter="cancelCloseTimer()">
  <div id="live-audio-tab" onclick="toggleAudioPanel()">
    🎙️ Live
  </div>
  <div id="live-audio-content">
    <audio id="live-audio-player" controls preload="none">
      <source src="/stream">
    </audio>
  </div>
</div>
<script>
  let audioPanelTimer;
  function toggleAudioPanel() {
    document.getElementById('live-audio-panel').classList.toggle('open');
  }
  function startCloseTimer() {
    audioPanelTimer = setTimeout(() => {
      document.getElementById('live-audio-panel').classList.remove('open');
    }, 2000);
  }
  function cancelCloseTimer() {
    clearTimeout(audioPanelTimer);
  }
</script>
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
