import argparse
import json
import logging
import sys

from utils import notifications
from utils.helpers import DB_PATH, get_settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='path to config', required=True)
    parser.add_argument('--title', help='title', required=True)
    parser.add_argument('--body', help='path to body template', required=True)
    parser.add_argument('--detection', help='path to json encoded detection', required=True)
    args = parser.parse_args()

    conf = get_settings()
    conf['APPRISE_NOTIFICATION_TITLE'] = args.title
    conf['APPRISE_NOTIFY_EACH_DETECTION'] = '1'
    conf['APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY'] = '0'
    conf['APPRISE_NOTIFY_NEW_SPECIES'] = '0'

    notifications.APPRISE_CONFIG = args.config
    notifications.APPRISE_BODY = args.body

    f = open(args.detection, 'r')
    d = json.loads(f.read())

    logger = logging.getLogger()
    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    notifications.sendAppriseNotifications(f"{d['Sci_Name']}_{d['Com_Name']}", d['Confidence'], round(d['Confidence'] * 100), d['File_Name'],
                                           d['Date'], d['Time'], d['Week'], d['Lat'], d['Lon'], d['Cutoff'],
                                           d['Sens'], d['Overlap'], dict(conf), DB_PATH)
