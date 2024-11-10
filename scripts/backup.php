<?php

define('__ROOT__', dirname(dirname(__FILE__)));
require_once(__ROOT__.'/scripts/common.php');

$user = get_user();
$home = get_home();
ensure_authenticated('You must be authenticated to download backup files.');

set_timezone();
$date = new DateTime();
$date_str = $date->format("Ymd\\THis");

header("Content-Description: File Transfer");
header("Content-Type: application/octet-stream");
header("Content-Disposition: attachment; filename=\"backup-$date_str.tar\"");

$err=null;
set_time_limit(0);
passthru("sudo -u $user $home/BirdNET-Pi/scripts/backup_data.sh -a backup -f -", $err);
debug_log(strval($err));
exit();
