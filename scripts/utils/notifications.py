import apprise
import os
import socket
import sqlite3
from datetime import datetime
import requests
import html
import time as timeim

userDir = os.path.expanduser('~')
APPRISE_CONFIG = userDir + '/BirdNET-Pi/apprise.txt'
APPRISE_BODY = userDir + '/BirdNET-Pi/body.txt'
DB_PATH = userDir + '/BirdNET-Pi/scripts/birds.db'

apobj = None
images = {}
species_last_notified = {}


def notify(body, title, attached=""):
    global apobj
    if apobj is None:
        asset = apprise.AppriseAsset(
            plugin_paths=[
                userDir + "/.apprise/plugins",
                userDir + "/.config/apprise/plugins",
            ]
        )
        apobj = apprise.Apprise(asset=asset)
        config = apprise.AppriseConfig()
        config.add(APPRISE_CONFIG)
        apobj.add(config)

    if attached != "":
        apobj.notify(
            body=body,
            title=title,
            attach=attached,
        )
    else:
        apobj.notify(
            body=body,
            title=title,
        )


def sendAppriseNotifications(species, confidence, confidencepct, path,
                             date, time, week, latitude, longitude, cutoff,
                             sens, overlap, settings_dict, db_path=DB_PATH):
    def render_template(template, reason=""):
        ret = template.replace("$sciname", sciName) \
            .replace("$comname", comName) \
            .replace("$confidencepct", str(confidencepct)) \
            .replace("$confidence", str(confidence)) \
            .replace("$listenurl", listenurl) \
            .replace("$friendlyurl", friendlyurl) \
            .replace("$date", str(date)) \
            .replace("$time", str(time)) \
            .replace("$week", str(week)) \
            .replace("$latitude", str(latitude)) \
            .replace("$longitude", str(longitude)) \
            .replace("$cutoff", str(cutoff)) \
            .replace("$sens", str(sens)) \
            .replace("$flickrimage", image_url if "{" in body else "") \
            .replace("$image", image_url if "{" in body else "") \
            .replace("$overlap", str(overlap)) \
            .replace("$reason", reason)
        return ret
    # print(sendAppriseNotifications)
    # print(settings_dict)
    if os.path.exists(APPRISE_CONFIG) and os.path.getsize(APPRISE_CONFIG) > 0:

        title = html.unescape(settings_dict.get('APPRISE_NOTIFICATION_TITLE'))
        f = open(APPRISE_BODY, 'r')
        body = f.read()

        sciName, comName = species.split("_")

        APPRISE_ONLY_NOTIFY_SPECIES_NAMES = settings_dict.get('APPRISE_ONLY_NOTIFY_SPECIES_NAMES')
        if APPRISE_ONLY_NOTIFY_SPECIES_NAMES is not None and APPRISE_ONLY_NOTIFY_SPECIES_NAMES.strip() != "":
            if any(bird.lower().replace(" ", "") in comName.lower().replace(" ", "") for bird in APPRISE_ONLY_NOTIFY_SPECIES_NAMES.split(",")):
                return

        APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2 = settings_dict.get('APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2')
        if APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2 is not None and APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2.strip() != "":
            if not any(bird.lower().replace(" ", "") in comName.lower().replace(" ", "") for bird in APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2.split(",")):
                return

        APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES = settings_dict.get('APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES')
        if APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES != "0":
            if species_last_notified.get(comName) is not None:
                try:
                    if int(timeim.time()) - species_last_notified[comName] < int(APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES):
                        return
                except Exception as e:
                    print("APPRISE NOTIFICATION EXCEPTION: "+str(e))
                    return

        # TODO: this all needs to be changed, we changed the caddy default to allow direct IP access, so birdnetpi.local shouldn't be relied on anymore
        try:
            websiteurl = settings_dict.get('BIRDNETPI_URL')
            if len(websiteurl) == 0:
                raise ValueError('Blank URL')
        except Exception:
            websiteurl = "http://"+socket.gethostname()+".local"

        listenurl = websiteurl+"?filename="+path
        friendlyurl = "[Listen here]("+listenurl+")"
        image_url = ""

        if "$flickrimage" in body or "$image" in body:
            if comName not in images:
                try:
                    url = f"http://localhost/api/v1/image/{sciName}"
                    resp = requests.get(url=url, timeout=10).json()
                    images[comName] = resp['data']['image_url']
                except Exception as e:
                    print("IMAGE API ERROR: "+str(e))
            image_url = images.get(comName, "")

        if settings_dict.get('APPRISE_NOTIFY_EACH_DETECTION') == "1":
            notify_body = render_template(body, "detection")
            notify_title = render_template(title, "detection")
            notify(notify_body, notify_title, image_url)
            species_last_notified[comName] = int(timeim.time())

        APPRISE_NOTIFICATION_NEW_SPECIES_DAILY_COUNT_LIMIT = 1  # Notifies the first N per day.
        if settings_dict.get('APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY') == "1":
            numberDetections = get_todays_count_for(db_path, sciName)
            if 0 < numberDetections <= APPRISE_NOTIFICATION_NEW_SPECIES_DAILY_COUNT_LIMIT:
                print("send the notification")
                notify_body = render_template(body, "first time today")
                notify_title = render_template(title, "first time today")
                notify(notify_body, notify_title, image_url)
                species_last_notified[comName] = int(timeim.time())

        if settings_dict.get('APPRISE_NOTIFY_NEW_SPECIES') == "1":
            numberDetections = get_this_weeks_count_for(db_path, sciName)
            if 0 < numberDetections <= 5:
                reason = f"only seen {numberDetections} times in last 7d"
                notify_body = render_template(body, reason)
                notify_title = render_template(title, reason)
                notify(notify_body, notify_title, image_url)
                species_last_notified[comName] = int(timeim.time())


def get_todays_count_for(db_path, sci_name):
    today = datetime.now().strftime("%Y-%m-%d")
    select_sql = f"SELECT COUNT(*) FROM detections WHERE Date = DATE('{today}') AND Sci_Name = '{sci_name}'"
    records = get_records(db_path, select_sql)
    return records[0][0] if records else 0


def get_this_weeks_count_for(db_path, sci_name):
    today = datetime.now().strftime("%Y-%m-%d")
    select_sql = f"SELECT COUNT(*) FROM detections WHERE Date >= DATE('{today}', '-7 day') AND Sci_Name = '{sci_name}'"
    records = get_records(db_path, select_sql)
    return records[0][0] if records else 0


def get_records(db_path, select_sql):
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.cursor()
        cur.execute(select_sql)
        records = cur.fetchall()
        con.close()
    except sqlite3.Error as e:
        print(f"Database busy: {e}")
        timeim.sleep(2)
        records = []
    return records


if __name__ == "__main__":
    print("notfications")
