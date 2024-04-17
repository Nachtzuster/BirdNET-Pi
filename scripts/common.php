<?php
//Database Queries
include_once 'common_db.php';

if (session_status() !== PHP_SESSION_ACTIVE)
  session_start();

function ensure_db_ok($sql_stmt) {
  if ($sql_stmt == False) {
    echo "Database is busy";
    header("refresh:1;");
    exit;
  }
}

function set_timezone() {
  if (!isset($_SESSION['my_timezone'])) {
    $_SESSION['my_timezone'] = trim(shell_exec('timedatectl show --value --property=Timezone'));
  }
  date_default_timezone_set($_SESSION['my_timezone']);
}

function get_config($force_reload = false) {
  $mtime = stat('/etc/birdnet/birdnet.conf')["mtime"];
  if (isset($_SESSION['my_config_version']) && $_SESSION['my_config_version'] !== $mtime) {
    $force_reload = true;
  }
  if (!isset($_SESSION['my_config']) || $force_reload) {
    $source = preg_replace("~^#+.*$~m", "", file_get_contents('/etc/birdnet/birdnet.conf'));
    $my_config = parse_ini_string($source);
    if ($my_config) {
      $_SESSION['my_config'] = $my_config;
    } else {
      syslog(LOG_ERR, "Cannot parse config");
    }
    $_SESSION['my_config_version'] = $mtime;
  }
  return $_SESSION['my_config'];
}

function get_user() {
  $config = get_config();
  $user = $config['BIRDNET_USER'];
  return $user;
}

function get_home() {
  $home = '/home/' . get_user();
  return $home;
}

function get_sitename() {
  $config = get_config();

  if ($config["SITE_NAME"] == "") {
    $site_name = "BirdNET-Pi";
  } else {
    $site_name = $config['SITE_NAME'];
  }
  return $site_name;
}

function get_service_mount_name() {
  $home = get_home();
  $service_mount = trim(shell_exec("systemd-escape -p --suffix=mount " . $home . "/BirdSongs/StreamData"));
  return $service_mount;
}

function is_authenticated() {
  $ret = false;
  if (isset($_SERVER['PHP_AUTH_USER']) && isset($_SERVER['PHP_AUTH_PW'])) {
    $config = get_config();
    $ret = ($_SERVER['PHP_AUTH_PW'] == $config['CADDY_PWD'] && $_SERVER['PHP_AUTH_USER'] == 'birdnet');
  }
  return $ret;
}

function ensure_authenticated($error_message = 'You cannot edit the settings for this installation') {
  if (!is_authenticated()) {
    header('WWW-Authenticate: Basic realm="My Realm"');
    header('HTTP/1.0 401 Unauthorized');
    echo '<table><tr><td>' . $error_message . '</td></tr></table>';
    exit;
  }
}

function debug_log($message) {
  if (is_bool($message)) {
    $message = $message ? 'true' : 'false';
  }
  error_log($message . "\n", 3, $_SERVER['DOCUMENT_ROOT'] . "/debug_log.log");
}

/**
 * Returns the start and end dates for last week
 *
 * @return string[]
 */
function get_last_weeks_dates()
{
	$startdate = strtotime('last sunday') - (7 * 86400);
	$enddate = strtotime('last sunday') - (1 * 86400);

	return ['start_date' => $startdate, 'end_date' => $enddate];
}