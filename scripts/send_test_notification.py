import argparse
import datetime
import logging
import sys

from utils import notifications
from utils.helpers import get_settings
from utils.db import get_latest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='path to config', required=True)
    parser.add_argument('--title', help='title', required=True)
    parser.add_argument('--body', help='path to body template', required=True)
    args = parser.parse_args()

    conf = get_settings()
    conf['APPRISE_NOTIFICATION_TITLE'] = args.title
    conf['APPRISE_NOTIFY_EACH_DETECTION'] = '1'
    conf['APPRISE_NOTIFY_NEW_SPECIES_EACH_DAY'] = '0'
    conf['APPRISE_NOTIFY_NEW_SPECIES'] = '0'

    notifications.APPRISE_CONFIG = args.config
    notifications.APPRISE_BODY = args.body

    logger = logging.getLogger()
    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    d = get_latest()
    if not d:
        now = datetime.datetime.now()
        d = {'Sci_Name': 'Aptenodytes patagonicus', 'Com_Name': 'King Penguin', 'Confidence': 0.84, 'File_Name': 'this_is_not_a_file.mp3',
             'Date': now.strftime('%Y-%m-%d'), 'Time': now.strftime("%H:%M:%S"), 'Week': now.isocalendar()[1],
             'Lat': conf.getfloat('LATITUDE'), 'Lon': conf.getfloat('LONGITUDE'), 'Cutoff': conf.getfloat('CONFIDENCE'),
             'Sens': conf.getfloat('SENSITIVITY'), 'Overlap': conf.getfloat('OVERLAP')}

    notifications.sendAppriseNotifications(d['Sci_Name'], d['Com_Name'], d['Confidence'], round(d['Confidence'] * 100), d['File_Name'], d['Date'], d['Time'],
                                           d['Week'], d['Lat'], d['Lon'], d['Cutoff'], d['Sens'], d['Overlap'])
