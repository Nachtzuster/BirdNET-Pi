<?php

define('__ROOT__', dirname(dirname(__FILE__)));
require_once(__ROOT__ . '/scripts/common.php');

$config = get_config();
$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$requestMethod = $_SERVER['REQUEST_METHOD'];

if ($requestMethod !== 'GET') {
  sendResponse405();
}

function api_is_local() {
  $ip = $_SERVER['REMOTE_ADDR'] ?? '';
  return $ip === '127.0.0.1' || $ip === '::1' || $ip === '::ffff:127.0.0.1';
}

if (preg_match('#^/api/v1/image/(\S+)$#', $requestUri, $matches)) {
  if (!api_is_local() && !is_authenticated()) {
    http_response_code(401);
    header('WWW-Authenticate: Basic realm="BirdNET-Pi"');
    echo json_encode(["message" => "Unauthorized"]);
    exit;
  }
  if (empty($config["IMAGE_PROVIDER"])) {
    http_response_code(404);
    echo "Error 404! Image provider disabled.";
    exit;
  }
  $sci_name = urldecode($matches[1]);
  if (!preg_match('/^[A-Za-z .\'-]{1,64}$/', $sci_name)) {
    http_response_code(400);
    echo "Error 400! Invalid species name.";
    exit;
  }
  if ($config["IMAGE_PROVIDER"] === 'FLICKR') {
    $image_provider = new Flickr();
  } else {
    $image_provider = new Wikipedia();
  }
  $result = $image_provider->get_image($sci_name);

  if ($result == false) {
    http_response_code(404);
    echo "Error 404! No image found!";
  } else {
    http_response_code(200);
    header('Content-Type: application/json');
    echo json_encode([
      "status" => "success",
      "message" => "successfully image data from database",
      "data" => $result
    ]);
  }
} else {
  http_response_code(404);
  echo "Error 404! No route found!";
}

function sendResponse405() {
  http_response_code(405);
  echo json_encode(["message" => "Method Not Allowed"]);
}
