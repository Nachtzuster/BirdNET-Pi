<?php

/* Prevent XSS input */
$_GET   = filter_input_array(INPUT_GET, FILTER_SANITIZE_STRING);
$_POST  = filter_input_array(INPUT_POST, FILTER_SANITIZE_STRING);

error_reporting(E_ERROR);
ini_set('display_errors', 1);
require_once 'scripts/common.php';

$config = get_config();
$home = get_home();
$user = get_user();
$CLIENT_ID = 'birdnet-pi';
$UPLOADSITE_USER = $config['UPLOADSITE_USER'];
$UPLOADSITE_PASS = $config['UPLOADSITE_PASS'];
$UPLOADSITE_SITE = $config['UPLOADSITE_SITE'];
$cmd="cd ".$home."/BirdNET-Pi && sudo -u ".$user." git rev-list --max-count=1 HEAD";
$curr_hash = shell_exec($cmd);
$observationorgsites = ["observation.org", "waarneming.nl", "waarnemingen.be", "observations.be"];

// Get the url corresponding to the already uploaded observation
function getOBSURL($UPLOADSITE_SITE, $UUID) {
    global $observationorgsites;
    if (in_array($UPLOADSITE_SITE, $observationorgsites)) {
        return "https://" . $UPLOADSITE_SITE . "/observation/" . $UUID;
    } elseif ($UPLOADSITE_SITE == "inaturalist.org") {
        return "https://www.inaturalist.org/observations/" . $UUID;
    }
    return null;
}

// Fetch the token
function getOBSToken($UPLOADSITE_SITE) {
    global $CLIENT_ID, $UPLOADSITE_USER, $UPLOADSITE_PASS, $observationorgsites, $curr_hash;
    if (in_array($UPLOADSITE_SITE, $observationorgsites)) {
        $ch = curl_init();

        curl_setopt($ch, CURLOPT_URL, 'https://' . $UPLOADSITE_SITE . '/api/v1/oauth2/token/');
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_POST, 1);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query(array('client_id' => $CLIENT_ID, 'grant_type' => 'password', 'email' => $UPLOADSITE_USER, 'password' => $UPLOADSITE_PASS)));

        $headers = array();
        $headers[] = 'Content-Type: application/x-www-form-urlencoded';
        $headers[] = 'User-Agent: BirdNet-Pi/' . $curr_hash;
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

        $result = curl_exec($ch);
        if (curl_errno($ch)) {
            echo 'Error:' . curl_error($ch);
            curl_close($ch);
            return null;
        }
        curl_close($ch);

        $result_array = json_decode($result, true);
        return $result_array['access_token'];
    }
    return null;
}

function getSpeciesId($sciname, $comname) {
    // Define the API URLs
    $urlSciname = "https://observation.org/api/v1/species/search/?q=" . urlencode($sciname);

    // Function to perform the cURL request
    function performCurlRequest($url) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('Accept-Language: en'));
        $response = curl_exec($ch);
        curl_close($ch);
        return $response;
    }

    // Perform the first search with scientific name
    $response = performCurlRequest($urlSciname);
    $data = json_decode($response, true);

    // Check if the response contains data and has exactly one match
    if (!empty($data) && count($data) === 1) {
        return $data[0]['id'];
    }

    // If no data or more than one match, perform the second search with common name
    $comname = get_com_en_name($sciname);
    $urlComname = "https://observation.org/api/v1/species/search/?q=" . urlencode($comname);
    $response = performCurlRequest($urlComname);
    $data = json_decode($response, true);

    // Check if the response contains data and has exactly one match
    if (!empty($data) && count($data) === 1) {
        return $data[0]['id'];
    }

    // Return an error message if no data or more than one match found in either search
    return "Error: No unique match found for either scientific name or common name.";
}

// Prepare the observation data
function getObservationData($filename) {
    global $home;
    $db = new SQLite3('./scripts/birds.db', SQLITE3_OPEN_READONLY);
    $db->busyTimeout(5000);
    $statement2 = $db->prepare('SELECT * FROM detections WHERE File_name = :filename ORDER BY Date DESC, Time DESC');
    $statement2->bindValue(':filename', $filename);
    ensure_db_ok($statement2);
    $result2 = $statement2->execute();
    
    // Initialize variables to null
    $comname = $date = $time = $latitude = $longitude = null;
    
    while ($results = $result2->fetchArray(SQLITE3_ASSOC)) {
        $comname = $results['Com_Name'];
        $sciname = $results['Sci_Name'];
        $filename = $results['File_Name'];
        $date = $results['Date'];
        $time = $results['Time'];
        $latitude = $results['Lat'];
        $longitude = $results['Lon'];
    }

    // Check if required data is available
    if (!$date || !$time || !$latitude || !$longitude) {
        echo 'Warning: Required observation data is missing.';
        return null;
    }

    // Get observation ID
    $OBS_ID = fetchSpeciesId($sciname, $comname);
    if (strpos($OBS_ID, "Error:") === 0) {
        echo "Error: cannot fetch Species ID with message: " . $OBS_ID;
        return null;
    }

    // Prepare new observation data
    $OBS_DATA = array(
        'species' => $OBS_ID,
        'date' => $date,
        'time' => $time,
        'point' => "POINT($latitude $longitude)",
        'external_reference' => $filename,
        'method' => 'heard'
    );

    // Add sound if relevant
    $comname = preg_replace('/ /', '_', $comname);
    $filepath = $home . "/BirdSongs/Extracted/By_Date/" . $date . "/" . $comname . "/" . $filename;
    if (file_exists($filepath)) {
        $file_parts = pathinfo($filepath);
        if ($file_parts['extension'] == 'mp3' || $file_parts['extension'] == 'wav') {
            $cfile = new CURLFile($filepath, 'audio/mpeg', basename($filepath));
            $OBS_DATA['upload_sounds'] = $cfile;
        } else {
            echo 'Warning: audio file is not a MP3 or WAV file, it will not be added (' . $filename . ')';
        }
    } else {
        echo 'Warning: audio file does not exist (' . $filepath . ')';
    }

    // Return json value
    return $OBS_DATA;
}

// Save to file
function postfile($OBS_ID, $UPLOADSITE_SITE, $filename) {
    global $home;
    $file_path = $home . '/BirdNET-Pi/scripts/uploaded_observations_list.txt';

    // Check if the file exists
    if (!file_exists($file_path)) {
        $header = "uuid;uploadsite;filename\n";
        $result = file_put_contents($file_path, $header);
        if ($result === false) {
            echo "Failed to create or write to file: $file_path";
            return false;
        }
    }

    // Check if the filename already exists in the file
    $existing_content = file_get_contents($file_path);
    if (strpos($existing_content, $filename) !== false) {
        echo "File '$filename' already exists in the list.\n";
        return true; // No need to add duplicate content
    }

    // Verify that all fields have data
    if (empty($OBS_ID) || empty($UPLOADSITE_SITE) || empty($filename)) {
        echo "Invalid data: OBS_ID, UPLOADSITE_SITE, or filename is empty.\n";
        return false;
    }

    // Append the new data
    $data = "$OBS_ID;$UPLOADSITE_SITE;$filename\n";
    $result = file_put_contents($file_path, $data, FILE_APPEND);
    if ($result === false) {
        echo "Failed to append data to file: $file_path";
        return false;
    }

    return true;
}

// Fetch all existing observations and allocated to birdnet-pi observations
function getOBSUploaded($UPLOADSITE_SITE,$UPLOADSITE_USER) {
    global $CLIENT_ID, $observationorgsites;

    // Check if both input variables are provided
    if (empty($UPLOADSITE_SITE) || empty($UPLOADSITE_USER)) {
        echo "Error: Both site and user must be specified. Have you clicked on the save button in the settings ?\n";
        return;
    }

    if (in_array($UPLOADSITE_SITE, $observationorgsites)) {
        $url = "https://observation.org/api/v1/user/$UPLOADSITE_USER/observations/";
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        $output = curl_exec($ch);
        curl_close($ch);
        $data = json_decode($output, true);

        if (isset($data['results']) && is_array($data['results'])) {
            foreach ($data['results'] as $observation) {
                if (isset($observation['external_reference']) && !empty($observation['external_reference'])) {
                    if (strpos($observation['external_reference'], 'birdnet') !== false) {
                        postfile($observation['id'], $UPLOADSITE_SITE, $filename);
                    }
                }
            }
            echo "All observations in $UPLOADSITE_SITE were synced to the local database.\n";
        } else {
            echo "No uploaded observations found in $UPLOADSITE_SITE for user $UPLOADSITE_USER.\n";
        }
    } else {
        echo "Invalid site: $UPLOADSITE_SITE\n";
    }
}

// Post the observation data
function postOBS($UPLOADSITE_SITE, $OBSTOKEN, $filename, $uploadnotes) {
    global $observationorgsites, $version;

    // Fetch observation data
    $OBS_DATA = getObservationData($filename);

    // Check if OBS_DATA is not empty or null
    if (!$OBS_DATA) {
        echo 'Error: Observation data is missing or invalid.';
        return;
    }

    // Append notes
    if (!empty($uploadnotes)) {
        $OBS_DATA['notes'] = $uploadnotes;
    }

    if (in_array($UPLOADSITE_SITE, $observationorgsites)) {
        // Prepare headers
        $headers = array(
            'Authorization: Bearer ' . $OBSTOKEN,
            'User-Agent: BirdNet-Pi/' . $version
        );
        $url = "https://" . $UPLOADSITE_SITE . "/api/v1/observations/create/";

        // Initialize cURL
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $OBS_DATA);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array_merge($headers, array("Content-Type: multipart/form-data")));

        // Execute cURL request
        $response = curl_exec($ch);
        $http_status = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        // Check for errors
        if ($response === false) {
            echo 'Error: ' . curl_error($ch);
        } else {
            // Decode the JSON response
            $json_response = json_decode($response, true);

            // Determine message based on HTTP status code
            if ($http_status == 201) {
                echo 'OK : upload successful to '.$json_response['permalink'];
            } elseif ($http_status == 200) {
                echo 'OK : update successful '.$json_response['permalink'];
            } else {
                echo 'Error: ' . $http_status . ' - ' . $json_response['error'];
            }
    
            // Extract ID if available
            $OBS_ID = isset($json_response['id']) ? $json_response['id'] : null;
            // Save to file
            postfile($OBS_ID,$UPLOADSITE_SITE,$filename);
            $posted = postfile($OBS_ID, $UPLOADSITE_SITE, $filename);
            if ($posted) {
                echo "Data posted successfully.";
            } else {
                echo "Failed to post data.";
            }
        }

        // Close cURL
        curl_close($ch);
    }
}

?>
