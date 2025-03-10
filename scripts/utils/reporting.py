import glob
import json
import logging
import os
import sqlite3
import subprocess
from time import sleep

from tzlocal import get_localzone
import requests

from .helpers import get_settings, ParseFileName, Detection, DB_PATH
from .notifications import sendAppriseNotifications
from .birdweather import post_soundscape_to_birdweather, post_detection_to_birdweather

log = logging.getLogger(__name__)


def get_safe_title(title):
    result = subprocess.run(['iconv', '-f', 'utf8', '-t', 'ascii//TRANSLIT'],
                            check=True, input=title.encode('utf-8'), capture_output=True)
    ret = result.stdout.decode('utf-8')
    return ret


def extract(in_file, out_file, start, stop):
    result = subprocess.run(['sox', '-V1', f'{in_file}', f'{out_file}', 'trim', f'={start}', f'={stop}'],
                            check=True, capture_output=True)
    ret = result.stdout.decode('utf-8')
    err = result.stderr.decode('utf-8')
    if err:
        raise RuntimeError(f'{ret}:\n {err}')
    return ret


def extract_safe(in_file, out_file, start, stop):
    conf = get_settings()
    # This section sets the SPACER that will be used to pad the audio clip with
    # context. If EXTRACTION_LENGTH is 10, for instance, 3 seconds are removed
    # from that value and divided by 2, so that the 3 seconds of the call are
    # within 3.5 seconds of audio context before and after.
    try:
        ex_len = conf.getint('EXTRACTION_LENGTH')
    except ValueError:
        ex_len = 6
    spacer = (ex_len - 3) / 2
    safe_start = max(0, start - spacer)
    safe_stop = min(conf.getint('RECORDING_LENGTH'), stop + spacer)

    extract(in_file, out_file, safe_start, safe_stop)


def spectrogram(in_file, title, comment, raw=False):
    args = ['sox', '-V1', f'{in_file}', '-n', 'remix', '1', 'rate', '24k', 'spectrogram',
            '-t', f'{get_safe_title(title)}', '-c', f'{comment}', '-o', f'{in_file}.png']
    args += ['-r'] if raw else []
    result = subprocess.run(args, check=True, capture_output=True)
    ret = result.stdout.decode('utf-8')
    err = result.stderr.decode('utf-8')
    if err:
        raise RuntimeError(f'{ret}:\n {err}')
    return ret


def extract_detection(file: ParseFileName, detection: Detection):
    conf = get_settings()
    new_file_name = f'{detection.common_name_safe}-{detection.confidence_pct}-{detection.date}-birdnet-{file.RTSP_id}{detection.time}.{conf["AUDIOFMT"]}'
    new_dir = os.path.join(conf['EXTRACTED'], 'By_Date', f'{detection.date}', f'{detection.common_name_safe}')
    new_file = os.path.join(new_dir, new_file_name)
    if os.path.isfile(new_file):
        log.warning('Extraction exists. Moving on: %s', new_file)
    else:
        os.makedirs(new_dir, exist_ok=True)
        extract_safe(
            file.file_name,
            new_file,
            (detection.start_datetime - file.file_date).seconds,
            (detection.stop_datetime - file.file_date).seconds,
        )
        spectrogram(new_file, detection.common_name, new_file.replace(os.path.expanduser('~/'), ''))
    return new_file


def write_to_db(file: ParseFileName, detection: Detection):
    conf = get_settings()
    # Connect to SQLite Database
    for attempt_number in range(3):
        try:
            con = sqlite3.connect(DB_PATH)
            cur = con.cursor()
            cur.execute("INSERT INTO detections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (detection.date, detection.time, detection.scientific_name, detection.common_name, detection.confidence,
                         conf['LATITUDE'], conf['LONGITUDE'], conf['CONFIDENCE'], str(detection.week), conf['SENSITIVITY'],
                         conf['OVERLAP'], os.path.basename(detection.file_name_extr)))
            # (Date, Time, Sci_Name, Com_Name, str(score),
            # Lat, Lon, Cutoff, Week, Sens,
            # Overlap, File_Name))

            con.commit()
            con.close()
            break
        except BaseException as e:
            log.warning("Database busy: %s", e)
            sleep(2)


def summary(file: ParseFileName, detection: Detection):
    # Date;Time;Sci_Name;Com_Name;Confidence;Lat;Lon;Cutoff;Week;Sens;Overlap
    # 2023-03-03;12:48:01;Phleocryptes melanops;Wren-like Rushbird;0.76950216;-1;-1;0.7;9;1.25;0.0
    conf = get_settings()
    s = (f'{detection.date};{detection.time};{detection.scientific_name};{detection.common_name};'
         f'{detection.confidence};'
         f'{conf["LATITUDE"]};{conf["LONGITUDE"]};{conf["CONFIDENCE"]};{detection.week};{conf["SENSITIVITY"]};'
         f'{conf["OVERLAP"]}')
    return s


def write_to_file(file: ParseFileName, detection: Detection):
    with open(os.path.expanduser('~/BirdNET-Pi/BirdDB.txt'), 'a') as rfile:
        rfile.write(f'{summary(file, detection)}\n')


def update_json_file(file: ParseFileName, detections: [Detection]):
    if file.RTSP_id is None:
        mask = f'{os.path.dirname(file.file_name)}/*.json'
    else:
        mask = f'{os.path.dirname(file.file_name)}/*{file.RTSP_id}*.json'
    for f in glob.glob(mask):
        log.debug(f'deleting {f}')
        os.remove(f)
    write_to_json_file(file, detections)


def write_to_json_file(file: ParseFileName, detections: [Detection]):
    conf = get_settings()
    json_file = f'{file.file_name}.json'
    log.debug(f'WRITING RESULTS TO {json_file}')
    dets = {'file_name': os.path.basename(json_file), 'timestamp': file.iso8601, 'delay': conf['RECORDING_LENGTH'],
            'detections': [{"start": (det.start_datetime - file.file_date).seconds, "common_name": det.common_name, "confidence": det.confidence} for det in
                           detections]}
    with open(json_file, 'w') as rfile:
        rfile.write(json.dumps(dets))
    log.debug(f'DONE! WROTE {len(detections)} RESULTS.')


def apprise(file: ParseFileName, detections: [Detection]):
    species_apprised_this_run = []
    conf = get_settings()

    for detection in detections:
        # Apprise of detection if not already alerted this run.
        if detection.species not in species_apprised_this_run:
            try:
                sendAppriseNotifications(detection.species, str(detection.confidence), str(detection.confidence_pct),
                                         os.path.basename(detection.file_name_extr), detection.date, detection.time, str(detection.week),
                                         conf['LATITUDE'], conf['LONGITUDE'], conf['CONFIDENCE'], conf['SENSITIVITY'],
                                         conf['OVERLAP'], dict(conf), DB_PATH)
            except BaseException as e:
                log.exception('Error during Apprise:', exc_info=e)

            species_apprised_this_run.append(detection.species)


def post_current_detections_to_birdweather(file: ParseFileName, detections: [Detection]):
    """Post to BirdWeather detections that were just performed.

    This function relies on the .wav audio file temporarily stored in "StreamData" to post a
    soundscape to BirdWeather.
    """
    conf = get_settings()
    if conf['BIRDWEATHER_ID'] == "":
        return
    if detections:
        soundscape_id = post_soundscape_to_birdweather(
            conf["BIRDWEATHER_ID"], file.file_date.astimezone(get_localzone()), file.file_name
        )
        if soundscape_id is None:
            return
        for detection in detections:

            post_detection_to_birdweather(
                detection,
                soundscape_id,
                file.file_date,
                conf["BIRDWEATHER_ID"],
                conf['LATITUDE'],
                conf['LONGITUDE'],
                conf['MODEL'],
            )


def heartbeat():
    conf = get_settings()
    if conf['HEARTBEAT_URL']:
        try:
            result = requests.get(url=conf['HEARTBEAT_URL'], timeout=10)
            log.info('Heartbeat: %s', result.text)
        except BaseException as e:
            log.error('Error during heartbeat: %s', e)
