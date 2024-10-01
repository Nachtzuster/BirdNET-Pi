<?php

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

function get_com_en_name($sci_name) {
  if (!isset($_labels_flickr)) {
    $_labels_flickr = file(get_home() . "/BirdNET-Pi/model/labels_flickr.txt");
  }
  $engname = null;
  foreach ($_labels_flickr as $label) {
    if (trim(explode("_", $label)[0]) === $sci_name) {
      $engname = trim(explode("_", $label)[1]);
      break;
    }
  }
  return $engname;
}

function get_sci_name($com_name) {
  if (!isset($_labels)) {
    $_labels = file(get_home() . "/BirdNET-Pi/model/labels.txt");
  }
  $sciname = null;
  foreach ($_labels as $label) {
    if (trim(explode("_", $label)[1]) === $com_name) {
      $sciname = trim(explode("_", $label)[0]);
      break;
    }
  }
  return $sciname;
}

define('DB', './scripts/flickr.db');

class Flickr {

  private $flickr_api_key = null;
  private $args = "&license=2%2C3%2C4%2C5%2C6%2C9&orientation=square,portrait";
  private $blacklisted_ids = [];
  private $db = null;
  private $licenses_urls = [];
  private $labels_flickr = null;
  private $flickr_email = null;
  private $comnameprefix = "%20bird";

  public function __construct() {
    $tbl_def = "CREATE TABLE images (sci_name VARCHAR(63) NOT NULL PRIMARY KEY, com_en_name VARCHAR(63) NOT NULL, image_url VARCHAR(63) NOT NULL, title VARCHAR(31) NOT NULL, id VARCHAR(31) NOT NULL UNIQUE, author_url VARCHAR(63) NOT NULL, license_url VARCHAR(63) NOT NULL, date_created DATE)";
    try {
      $db = new SQLite3(DB, SQLITE3_OPEN_READWRITE);
    } catch (Exception $ex) {
      $db = new SQLite3(DB);
      $db->exec($tbl_def);
      $db->exec('CREATE TABLE source (ID INTEGER PRIMARY KEY, email VARCHAR(63), uid VARCHAR(63), date_created DATE)');
    }
    $db->busyTimeout(1000);
    $this->db = $db;

    $blacklisted = get_home() . "/BirdNET-Pi/scripts/blacklisted_images.txt";
    if (file_exists($blacklisted)) {
      $blacklisted_file = file($blacklisted);
      if ($blacklisted_file) {
        $this->blacklisted_ids = array_map('trim', $blacklisted_file);
      }
    }
    $this->flickr_api_key = get_config()["FLICKR_API_KEY"];
    $this->flickr_email = get_config()["FLICKR_FILTER_EMAIL"];
    $source = $this->get_uid_from_db();
    if ($source['email'] !== $this->flickr_email) {
      // reset the DB
      $this->db->exec("DROP TABLE images; " . $tbl_def);
      if (!empty($this->flickr_email)) {
        $source = $this->get_uid_from_db();
        if ($source['email'] !== $this->flickr_email) {
          $this->get_uid_from_flickr();
          $source = $this->get_uid_from_db();
        }
      } else {
        $this->set_uid_in_db("");
      }
    }
    if (!empty($this->flickr_email)) {
      $this->args = "&user_id=" . $source['uid'];
      $this->comnameprefix = "";
    }
  }

  public function get_image($sci_name) {
    $image = $this->get_image_from_db($sci_name);
    if ($image !== false && in_array($image['id'], $this->blacklisted_ids)) {
      $image = false;
      $this->delete_image_from_db($sci_name);
    }
    if ($image !== false) {
      $now = new DateTime();
      $datetime = DateTime::createFromFormat("Y-m-d", $image['date_created']);
      $interval = $now->diff($datetime);
      // use the last digit of the id as a semi random number, so not all entries expire at the same time
      $expire_days = 15 + intval($image['id'][-1]);
      if ($interval->days > $expire_days) {
        $image = false;
      }
    }
    if ($image === false) {
      $this->get_from_flickr($sci_name);
      $image = $this->get_image_from_db($sci_name);
    }
    $photos_url = str_replace('/people/', '/photos/', $image['author_url'].'/'.$image['id']);
    $image['photos_url'] = $photos_url;
    return $image;
  }

  private function delete_image_from_db($sci_name) {
    $statement0 = $this->db->prepare('DELETE FROM images WHERE sci_name == :sci_name');
    $statement0->bindValue(':sci_name', $sci_name);
    $statement0->execute();
  }

  private function get_image_from_db($sci_name) {
    $statement0 = $this->db->prepare('SELECT sci_name, com_en_name, image_url, title, id, author_url, license_url, date_created FROM images WHERE sci_name == :sci_name');
    $statement0->bindValue(':sci_name', $sci_name);
    $result = $statement0->execute();
    $row = $result->fetchArray(SQLITE3_ASSOC);
    return $row;
  }

  private function set_image_in_db($sci_name, $com_en_name, $image_url, $title, $id, $author_url, $license_url) {
    $statement0 = $this->db->prepare("INSERT OR REPLACE INTO images VALUES (:sci_name, :com_en_name, :image_url, :title, :id, :author_url, :license_url, DATE(\"now\"))");
    $statement0->bindValue(':sci_name', $sci_name);
    $statement0->bindValue(':com_en_name', $com_en_name);
    $statement0->bindValue(':image_url', $image_url);
    $statement0->bindValue(':title', $title);
    $statement0->bindValue(':id', $id);
    $statement0->bindValue(':author_url', $author_url);
    $statement0->bindValue(':license_url', $license_url);
    $statement0->execute();
  }

  private function get_from_flickr($sci_name) {
    $engname = get_com_en_name($sci_name);

    $flickrjson = json_decode(file_get_contents("https://www.flickr.com/services/rest/?method=flickr.photos.search&api_key=" . $this->flickr_api_key . "&text=" . str_replace(" ", "%20", $engname) . $this->comnameprefix . "&sort=relevance" . $this->args . "&per_page=5&media=photos&format=json&nojsoncallback=1"), true)["photos"]["photo"];
    // could be null!!
    // Find the first photo that is not blacklisted or is not the specific blacklisted id
    $photo = null;
    foreach ($flickrjson as $flickrphoto) {
      if ($flickrphoto["id"] !== "4892923285" && !in_array($flickrphoto["id"], $this->blacklisted_ids)) {
        $photo = $flickrphoto;
        break;
      }
    }

    if ($photo === null) return;

    $license_url = "https://api.flickr.com/services/rest/?method=flickr.photos.getInfo&api_key=" . $this->flickr_api_key . "&photo_id=" . $photo["id"] . "&format=json&nojsoncallback=1";
    $license_response = file_get_contents($license_url);
    $license_id = json_decode($license_response, true)["photo"]["license"];
    $license_url = $this->get_license_url($license_id);

    $authorlink = "https://flickr.com/people/" . $photo["owner"];
    $imageurl = 'https://farm' . $photo["farm"] . '.static.flickr.com/' . $photo["server"] . '/' . $photo["id"] . '_' . $photo["secret"] . '.jpg';

    $this->set_image_in_db($sci_name, $engname, $imageurl, $photo["title"], $photo["id"], $authorlink, $license_url);
  }

  private function get_license_url($id) {
    if (empty($this->licenses_urls)) {
      $licenses_url = "https://api.flickr.com/services/rest/?method=flickr.photos.licenses.getInfo&api_key=" . $this->flickr_api_key . "&format=json&nojsoncallback=1";
      $licenses_response = file_get_contents($licenses_url);
      $licenses_data = json_decode($licenses_response, true)["licenses"]["license"];
      foreach ($licenses_data as $license) {
        $license_id = $license["id"];
        $license_url = $license["url"];
        $this->licenses_urls[$license_id] = $license_url;
      }
    }
    return $this->licenses_urls[$id];
  }

  public function get_uid_from_db() {
    $statement0 = $this->db->prepare('SELECT email, uid, date_created FROM source');
    $result = $statement0->execute();
    $row = $result->fetchArray(SQLITE3_ASSOC);
    return $row;
  }

  private function set_uid_in_db($uid) {
    $statement0 = $this->db->prepare("INSERT OR REPLACE INTO source VALUES (1, :email, :uid, DATE(\"now\"))");
    $statement0->bindValue(':email', $this->flickr_email);
    $statement0->bindValue(':uid', $uid);
    $result = $statement0->execute();
    $row = $result->fetchArray(SQLITE3_ASSOC);
    return $row;
  }

  private function get_uid_from_flickr() {
    $uid = json_decode(file_get_contents("https://www.flickr.com/services/rest/?method=flickr.people.findByEmail&api_key=" . $this->flickr_api_key . "&find_email=" . $this->flickr_email . "&format=json&nojsoncallback=1"), true)["user"]["nsid"];
    $this->set_uid_in_db($uid);
  }

}

function get_info_url($sciname){
  $engname = get_com_en_name($sciname);
  $config = get_config();
  if ($config['INFO_SITE'] === 'EBIRD'){
    require 'scripts/ebird.php';
    $ebird = $ebirds[$sciname];
    $language = $config['DATABASE_LANG'];
    $url = "https://ebird.org/species/$ebird?siteLanguage=$language";
    $url_title = "eBirds";
  } else {
    $engname_url = str_replace("'", '', str_replace(' ', '_', $engname));
    $url = "https://allaboutbirds.org/guide/$engname_url";
    $url_title = "All About Birds";
  }
  $ret = array(
      'URL' => $url,
      'TITLE' => $url_title
          );
  return $ret;
}

function get_color_scheme(){
  $config = get_config();
  if (strtolower($config['COLOR_SCHEME']) === 'dark'){
    return 'static/dark-style.css';
  } else {
    return 'style.css';
  }
}
