<?php

define('__ROOT__', dirname(dirname(__FILE__)));
require_once(__ROOT__ . '/scripts/common.php');

$config = get_config();
$requestUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$requestMethod = $_SERVER['REQUEST_METHOD'];

if ($requestMethod !== 'GET') {
  sendResponse405();
}

$db = new SQLite3(__ROOT__ . '/scripts/birds.db', SQLITE3_OPEN_READONLY);
$db->busyTimeout(1000);

if (preg_match('#^/api/v1/image/(\S+)$#', $requestUri, $matches)) {
  $flickr = new Flickr();
  $wikipedia = new Wikipedia();
  if ($config["IMAGE_PROVIDER"] === 'FLICKR') {
    $image_provider = $flickr;
    $fallback_provider = $wikipedia;
  } else {
    $image_provider = $wikipedia;
    $fallback_provider = $flickr;
  }
  $sci_name = urldecode($matches[1]);
  $result = $image_provider->get_image($sci_name, $fallback_provider);

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
} elseif (preg_match('#^/api/v1/analytics/activity$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 30;
  $stmt = $db->prepare('SELECT strftime("%H", Time) as Hour, COUNT(*) as Count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Hour ORDER BY Hour ASC');
  $result = $stmt->execute();
  $data = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $data[$row['Hour']] = $row['Count'];
  }
  
  // Fill empty hours with 0
  $final_data = [];
  for ($i = 0; $i < 24; $i++) {
    $hourStr = str_pad($i, 2, '0', STR_PAD_LEFT);
    $final_data[] = ["hour" => $hourStr, "count" => isset($data[$hourStr]) ? $data[$hourStr] : 0];
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode($final_data);

} elseif (preg_match('#^/api/v1/analytics/stats$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 7;
  
  // Total detections
  $stmt = $db->prepare('SELECT COUNT(*) as total FROM detections WHERE Date >= DATE("now", "-'.$days.' days")');
  $total = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['total'];
  
  // Unique species
  $stmt = $db->prepare('SELECT COUNT(DISTINCT(Sci_Name)) as unique_species FROM detections WHERE Date >= DATE("now", "-'.$days.' days")');
  $unique = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['unique_species'];
  
  // Avg confidence
  $stmt = $db->prepare('SELECT AVG(Confidence) as avg_conf FROM detections WHERE Date >= DATE("now", "-'.$days.' days")');
  $avg_conf = $stmt->execute()->fetchArray(SQLITE3_ASSOC)['avg_conf'];
  
  // Most common
  $stmt = $db->prepare('SELECT Com_Name, COUNT(*) as count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Sci_Name ORDER BY count DESC LIMIT 1');
  $most_common = $stmt->execute()->fetchArray(SQLITE3_ASSOC);

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode([
    "total_detections" => $total,
    "unique_species" => $unique,
    "avg_confidence" => round($avg_conf * 100, 1) . '%',
    "most_common" => $most_common ? $most_common['Com_Name'] : 'None',
    "most_common_count" => $most_common ? $most_common['count'] : 0,
    "days" => $days
  ]);

} elseif (preg_match('#^/api/v1/analytics/new_species$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 7;
  
  // Find species whose FIRST detection was within the last N days
  $stmt = $db->prepare('SELECT Com_Name, Sci_Name, MIN(Date) as first_date, MIN(Time) as first_time FROM detections GROUP BY Sci_Name HAVING first_date >= DATE("now", "-'.$days.' days") ORDER BY first_date DESC, first_time DESC');
  $result = $stmt->execute();
  $data = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $data[] = $row;
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode($data);

} elseif (preg_match('#^/api/v1/analytics/diversity$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 30;
  
  $stmt = $db->prepare('SELECT Date, COUNT(DISTINCT(Sci_Name)) as count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Date ORDER BY Date ASC');
  $result = $stmt->execute();
  
  $dates = [];
  $counts = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $dates[] = $row['Date'];
    $counts[] = $row['count'];
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode(["dates" => $dates, "counts" => $counts]);

} elseif (preg_match('#^/api/v1/analytics/detections$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 30;
  
  $stmt = $db->prepare('SELECT Date, COUNT(*) as count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Date ORDER BY Date ASC');
  $result = $stmt->execute();
  
  $dates = [];
  $counts = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $dates[] = $row['Date'];
    $counts[] = $row['count'];
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode(["dates" => $dates, "counts" => $counts]);

} elseif (preg_match('#^/api/v1/analytics/top_species$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 30;
  $limit = isset($_GET['limit']) && is_numeric($_GET['limit']) ? intval($_GET['limit']) : 10;
  
  $stmt = $db->prepare('SELECT Com_Name, COUNT(*) as Count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Com_Name ORDER BY Count DESC LIMIT '.$limit);
  $result = $stmt->execute();
  $data = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $data[] = ["species" => $row['Com_Name'], "count" => $row['Count']];
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode($data);

} elseif (preg_match('#^/api/v1/analytics/trends$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 30;
  
  // Get top 5 species first
  $stmt = $db->prepare('SELECT Com_Name, COUNT(*) as Count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Com_Name ORDER BY Count DESC LIMIT 5');
  $result = $stmt->execute();
  $top_species = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $top_species[] = $row['Com_Name'];
  }
  
  $data = [];
  $dates_array = [];
  
  for ($i = $days; $i >= 0; $i--) {
    $dates_array[] = date('Y-m-d', strtotime("-$i days"));
  }

  // Get daily counts for each top species
  foreach ($top_species as $species) {
    $stmt = $db->prepare('SELECT Date, COUNT(*) as Count FROM detections WHERE Com_Name = :com_name AND Date >= DATE("now", "-'.$days.' days") GROUP BY Date');
    $stmt->bindValue(':com_name', $species, SQLITE3_TEXT);
    $result = $stmt->execute();
    
    $species_data = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
      $species_data[$row['Date']] = $row['Count'];
    }
    
    // Fill empty dates with 0
    $final_species_data = [];
    foreach ($dates_array as $dateStr) {
      $final_species_data[] = isset($species_data[$dateStr]) ? $species_data[$dateStr] : 0;
    }
    
    $data[$species] = $final_species_data;
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode(["dates" => $dates_array, "series" => $data]);

} elseif (preg_match('#^/api/v1/analytics/patterns$#', $requestUri)) {
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 30;
  
  // Get top 5 species first
  $stmt = $db->prepare('SELECT Com_Name, COUNT(*) as Count FROM detections WHERE Date >= DATE("now", "-'.$days.' days") GROUP BY Com_Name ORDER BY Count DESC LIMIT 5');
  $result = $stmt->execute();
  $top_species = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $top_species[] = $row['Com_Name'];
  }
  
  $data = [];
  foreach ($top_species as $species) {
    $stmt = $db->prepare('SELECT strftime("%H", Time) as Hour, COUNT(*) as count FROM detections WHERE Com_Name = :com_name AND Date >= DATE("now", "-'.$days.' days") GROUP BY Hour ORDER BY Hour ASC');
    $stmt->bindValue(':com_name', $species, SQLITE3_TEXT);
    $result = $stmt->execute();
    
    $hourly_counts = array_fill(0, 24, 0);
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
      $hourly_counts[intval($row['Hour'])] = (float)$row['count'] / $days; // Average detections per hour
    }
    $data[$species] = $hourly_counts;
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode($data);

} elseif (preg_match('#^/api/v1/detections/recent$#', $requestUri)) {
  $limit = isset($_GET['limit']) && is_numeric($_GET['limit']) ? intval($_GET['limit']) : 20;
  $days = isset($_GET['days']) && is_numeric($_GET['days']) ? intval($_GET['days']) : 0;
  if ($limit > 100) $limit = 100;
  
  $date_filter = $days > 0 ? 'Date >= DATE("now", "-'.$days.' days")' : 'Date = DATE("now", "localtime")';
  $stmt = $db->prepare('SELECT Com_Name, Sci_Name, Confidence, Date, Time FROM detections WHERE '.$date_filter.' ORDER BY Date DESC, Time DESC LIMIT '.$limit);
  $result = $stmt->execute();
  $data = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $data[] = [
      "species" => $row['Com_Name'],
      "sci_name" => $row['Sci_Name'],
      "confidence" => round((float)$row['Confidence'], 4),
      "date" => $row['Date'],
      "time" => $row['Time']
    ];
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode($data);

} elseif (preg_match('#^/api/v1/detections/timeline$#', $requestUri)) {
  $date = isset($_GET['date']) && preg_match('/^\d{4}-\d{2}-\d{2}$/', $_GET['date']) ? $_GET['date'] : date('Y-m-d');

  $stmt = $db->prepare('SELECT Com_Name, Sci_Name, Confidence, Time, File_Name FROM detections WHERE Date = :date ORDER BY Time ASC');
  $stmt->bindValue(':date', $date, SQLITE3_TEXT);
  $result = $stmt->execute();

  $all = [];
  while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
    $all[] = $row;
  }

  // Group by hour
  $hours_data = [];
  $total_detections = 0;
  $species_set = [];
  $hour_counts = [];

  foreach ($all as $det) {
    $hour = intval(substr($det['Time'], 0, 2));
    if (!isset($hours_data[$hour])) $hours_data[$hour] = [];
    $hours_data[$hour][] = $det;
    $total_detections++;
    $species_set[$det['Sci_Name']] = true;
    $hour_counts[$hour] = ($hour_counts[$hour] ?? 0) + 1;
  }

  // Find peak hour
  $peak_hour = 0;
  $peak_count = 0;
  foreach ($hour_counts as $h => $c) {
    if ($c > $peak_count) { $peak_count = $c; $peak_hour = $h; }
  }

  // Cluster same-species detections within 5-minute windows per hour
  $hours_result = [];
  for ($h = 0; $h < 24; $h++) {
    $dets = $hours_data[$h] ?? [];
    if (empty($dets)) continue;

    $clusters = [];
    $used = array_fill(0, count($dets), false);

    for ($i = 0; $i < count($dets); $i++) {
      if ($used[$i]) continue;
      $used[$i] = true;

      $cluster_dets = [$dets[$i]];
      $sci = $dets[$i]['Sci_Name'];
      $last_time_secs = _time_to_secs($dets[$i]['Time']);

      for ($j = $i + 1; $j < count($dets); $j++) {
        if ($used[$j]) continue;
        if ($dets[$j]['Sci_Name'] !== $sci) continue;
        $t = _time_to_secs($dets[$j]['Time']);
        if ($t - $last_time_secs <= 300) { // 5 minutes
          $used[$j] = true;
          $cluster_dets[] = $dets[$j];
          $last_time_secs = $t;
        }
      }

      // Find best confidence in cluster
      $best_conf = 0;
      $det_list = [];
      foreach ($cluster_dets as $cd) {
        $conf = round((float)$cd['Confidence'], 4);
        if ($conf > $best_conf) $best_conf = $conf;
        $det_list[] = [
          'time' => $cd['Time'],
          'confidence' => $conf,
          'file' => $cd['File_Name']
        ];
      }

      $clusters[] = [
        'species' => $cluster_dets[0]['Com_Name'],
        'sci_name' => $sci,
        'count' => count($cluster_dets),
        'best_confidence' => $best_conf,
        'first_time' => $cluster_dets[0]['Time'],
        'last_time' => $cluster_dets[count($cluster_dets) - 1]['Time'],
        'detections' => $det_list
      ];
    }

    $hours_result[] = [
      'hour' => $h,
      'detection_count' => count($dets),
      'clusters' => $clusters
    ];
  }

  http_response_code(200);
  header('Content-Type: application/json');
  echo json_encode([
    'date' => $date,
    'total_detections' => $total_detections,
    'total_species' => count($species_set),
    'peak_hour' => $peak_hour,
    'hours' => $hours_result
  ]);

} else {
  http_response_code(404);
  echo json_encode(["status" => "error", "message" => "Error 404! No route found!"]);
}

function _time_to_secs($time_str) {
  $parts = explode(':', $time_str);
  return intval($parts[0]) * 3600 + intval($parts[1]) * 60 + intval($parts[2] ?? 0);
}

function sendResponse405() {
  http_response_code(405);
  echo json_encode(["status" => "error", "message" => "Method Not Allowed"]);
  exit;
}
