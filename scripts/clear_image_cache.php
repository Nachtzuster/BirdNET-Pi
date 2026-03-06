<?php
define('__ROOT__', dirname(dirname(__FILE__)));
require_once(__ROOT__ . '/scripts/common.php');

$flickr_db = __ROOT__ . '/scripts/flickr.db';
$wikipedia_db = __ROOT__ . '/scripts/wikipedia.db';

echo "Cleaning image caches...\n";

if (file_exists($flickr_db)) {
    unlink($flickr_db);
    echo "Removed $flickr_db\n";
}

if (file_exists($wikipedia_db)) {
    unlink($wikipedia_db);
    echo "Removed $wikipedia_db\n";
}

echo "Image caches cleared successfully.\n";
?>
