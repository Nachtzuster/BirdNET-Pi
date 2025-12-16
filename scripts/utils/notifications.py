import apprise
import os
import socket
import requests
import html
import time

from .db import get_todays_count_for, get_this_weeks_count_for
from .helpers import get_settings

userDir = os.path.expanduser('~')
APPRISE_CONFIG = userDir + '/BirdNET-Pi/apprise.txt'
APPRISE_BODY = userDir + '/BirdNET-Pi/body.txt'

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


def sendAppriseNotifications(sci_name, com_name, confidence, confidencepct, path, date, time_of_day, week, latitude, longitude, cutoff, sens, overlap):
    def render_template(template, reason=""):
        ret = template.replace("$sciname", sci_name) \
            .replace("$comname", com_name) \
            .replace("$confidencepct", str(confidencepct)) \
            .replace("$confidence", str(confidence)) \
            .replace("$listenurl", listenurl) \
            .replace("$friendlyurl", friendlyurl) \
            .replace("$date", str(date)) \
            .replace("$time", str(time_of_day)) \
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

    if not should_notify(com_name):
        return

    settings_dict = get_settings()
    title = html.unescape(settings_dict.get('APPRISE_NOTIFICATION_TITLE'))
    f = open(APPRISE_BODY, 'r')
    body = f.read()

    websiteurl = settings_dict.get('BIRDNETPI_URL')
    if websiteurl is None or len(websiteurl) == 0:
        websiteurl = f"http://{socket.gethostname()}.local"

    listenurl = f"{websiteurl}?filename={path}"
    friendlyurl = f"[Listen here]({listenurl})"

    image_url = ""
    if "$flickrimage" in body or "$image" in body:
        if com_name not in images:
            try:
                url = f"http://localhost/api/v1/image/{sci_name}"
                resp = requests.get(url=url, timeout=10).json()
                images[com_name] = resp['data']['image_url']
            except Exception as e:
                print("IMAGE API ERROR:", e)
        image_url = images.get(com_name, "")

    if settings_dict.get('APPRISE_NOTIFY_EACH_DETECTION') == "1":
        reason = "detection"
        notify_body = render_template(body, reason)
        notify_title = render_template(title, reason)
        notify(notify_body, notify_title, image_url)
        species_last_notified[com_name] = int(time.time())

    APPRISE_NOTIFICATION_NEW_SPECIES_DAILY_COUNT_LIMIT = 1  # Notifies the first N per day.
    if settings_dict.get('APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY') == "1":
        numberDetections = get_todays_count_for(sci_name)
        if 0 < numberDetections <= APPRISE_NOTIFICATION_NEW_SPECIES_DAILY_COUNT_LIMIT:
            reason = "first time today"
            notify_body = render_template(body, reason)
            notify_title = render_template(title, reason)
            notify(notify_body, notify_title, image_url)
            species_last_notified[com_name] = int(time.time())

    if settings_dict.get('APPRISE_NOTIFY_NEW_SPECIES') == "1":
        numberDetections = get_this_weeks_count_for(sci_name)
        if 0 < numberDetections <= 5:
            reason = f"only seen {numberDetections} times in last 7d"
            notify_body = render_template(body, reason)
            notify_title = render_template(title, reason)
            notify(notify_body, notify_title, image_url)
            species_last_notified[com_name] = int(time.time())


def should_notify(com_name):
    settings_dict = get_settings()
    if not (os.path.exists(APPRISE_CONFIG) and os.path.getsize(APPRISE_CONFIG) > 0):
        return False

    # check if this is an excluded species
    APPRISE_ONLY_NOTIFY_SPECIES_NAMES = settings_dict.get('APPRISE_ONLY_NOTIFY_SPECIES_NAMES')
    if APPRISE_ONLY_NOTIFY_SPECIES_NAMES is not None and APPRISE_ONLY_NOTIFY_SPECIES_NAMES.strip() != "":
        excluded_species = [bird.lower().replace(" ", "") for bird in APPRISE_ONLY_NOTIFY_SPECIES_NAMES.split(",")]
        if com_name.lower().replace(" ", "") in excluded_species:
            return False

    # check if this is an included species
    APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2 = settings_dict.get('APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2')
    if APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2 is not None and APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2.strip() != "":
        included_species = [bird.lower().replace(" ", "") for bird in APPRISE_ONLY_NOTIFY_SPECIES_NAMES_2.split(",")]
        if com_name.lower().replace(" ", "") not in included_species:
            return False

    # is it still too soon?
    APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES = settings_dict.get('APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES')
    if APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES != "0":
        if species_last_notified.get(com_name) is not None:
            try:
                if int(time.time()) - species_last_notified[com_name] < int(APPRISE_MINIMUM_SECONDS_BETWEEN_NOTIFICATIONS_PER_SPECIES):
                    return False
            except Exception as e:
                print("APPRISE NOTIFICATION EXCEPTION: " + str(e))
                return False

    return True


if __name__ == "__main__":
    print("notfications")
