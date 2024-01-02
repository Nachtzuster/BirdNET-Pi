import configparser
import datetime
import glob
import os
import re
from itertools import chain

import psutil
from tzlocal import get_localzone

_settings = None

DB_PATH = os.path.expanduser('~/BirdNET-Pi/scripts/birds.db')
THISRUN = os.path.expanduser('~/BirdNET-Pi/scripts/thisrun.txt')


def _load_settings(settings_path='/etc/birdnet/birdnet.conf', force_reload=False):
    global _settings
    if _settings is None or force_reload:
        with open(settings_path) as f:
            parser = configparser.ConfigParser()
            # preserve case
            parser.optionxform = lambda option: option
            lines = chain(("[top]",), f)
            parser.read_file(lines)
            _settings = parser['top']
    return _settings


def get_settings(settings_path='/etc/birdnet/birdnet.conf', force_reload=False):
    settings = _load_settings(settings_path, force_reload)
    return settings


def write_settings(file_name=THISRUN):
    settings = _load_settings()
    with open(file_name, 'w') as configfile:
        for key, value in settings.items():
            configfile.write(f'{key}={value}\n')


class Detection:
    def __init__(self, start_time, stop_time, species, confidence):
        self.start = float(start_time)
        self.stop = float(stop_time)
        self.confidence = float(confidence)
        self.confidence_pct = round(self.confidence * 100)
        self.species = species
        self.scientific_name = species.split('_')[0]
        self.common_name = species.split('_')[1]
        self.common_name_safe = self.common_name.replace("'", "").replace(" ", "_")
        self.file_name_extr = None


class ParseFileName:
    def __init__(self, file_name):
        self.file_name = file_name
        name = os.path.splitext(os.path.basename(file_name))[0]
        date_created = re.search('^[0-9]+-[0-9]+-[0-9]+', name).group()
        time_created = re.search('[0-9]+:[0-9]+:[0-9]+$', name).group()
        self.file_date = datetime.datetime.strptime(f'{date_created}T{time_created}', "%Y-%m-%dT%H:%M:%S")
        self.root = name

        ident_match = re.search("RTSP_[0-9]+-", file_name)
        self.RTSP_id = ident_match.group() if ident_match is not None else ""

    @property
    def date(self):
        current_date = self.file_date.strftime("%Y-%m-%d")
        return current_date

    @property
    def time(self):
        current_time = self.file_date.strftime("%H:%M:%S")
        return current_time

    @property
    def iso8601(self):
        current_iso8601 = self.file_date.astimezone(get_localzone()).isoformat()
        return current_iso8601

    @property
    def week(self):
        week = self.file_date.isocalendar()[1]
        return week


def is_file_closed(path):
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
                if path == item.path:
                    return False
        except psutil.AccessDenied:
            pass
    return True


def get_wav_files():
    conf = get_settings()
    files = (glob.glob(os.path.join(conf['RECS_DIR'], '*/*/*.wav')) +
             glob.glob(os.path.join(conf['RECS_DIR'], 'StreamData/*.wav')))
    files.sort()
    files = [os.path.join(conf['RECS_DIR'], file) for file in files]
    files = [file for file in files if is_file_closed(file)]
    return files
