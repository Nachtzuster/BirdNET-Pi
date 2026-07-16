import logging
import os
import os.path
import re
import signal
import sys
import threading
from queue import Queue
from subprocess import CalledProcessError

import inotify.adapters
from inotify.constants import IN_CLOSE_WRITE

from utils.analysis import load_global_model, run_analysis
from utils.helpers import get_settings, get_wav_files, get_analyzing_now_path
from utils.classes import ParseFileName
from utils.reporting import extract_detection, summary, write_to_file, write_to_db, apprise, bird_weather, heartbeat, \
    update_json_file

shutdown = False

log = logging.getLogger(__name__)


def sig_handler(sig_num, curr_stack_frame):
    global shutdown
    log.info('Caught shutdown signal %d', sig_num)
    shutdown = True


def main():
    load_global_model()
    conf = get_settings()
    i = inotify.adapters.Inotify()
    i.add_watch(os.path.join(conf['RECS_DIR'], 'StreamData'), mask=IN_CLOSE_WRITE)

    backlog = get_wav_files()

    # maxsize bounds the queue so reporting cannot fall behind: put() blocks once
    # a chunk is already waiting. This replaces an explicit join() per file, which
    # forced analysis and reporting to run strictly serially.
    report_queue = Queue(maxsize=1)
    thread = threading.Thread(target=handle_reporting_queue, args=(report_queue, ))
    thread.start()

    log.info('backlog is %d', len(backlog))
    for file_name in backlog:
        process_file(file_name, report_queue)
        if shutdown:
            break
    log.info('backlog done')

    empty_count = 0
    for event in i.event_gen():
        if shutdown:
            break

        if event is None:
            if empty_count > (conf.getint('RECORDING_LENGTH') * 2 + 30):
                log.error('no more notifications: restarting...')
                break
            empty_count += 1
            continue

        (_, type_names, path, file_name) = event
        if re.search('.wav$', file_name) is None:
            continue
        log.debug("PATH=[%s] FILENAME=[%s] EVENT_TYPES=%s", path, file_name, type_names)

        file_path = os.path.join(path, file_name)
        if file_path in backlog:
            # if we're very lucky, the first event could be for the file in the backlog that finished
            # while running get_wav_files()
            backlog = []
            continue

        process_file(file_path, report_queue)
        empty_count = 0

    # we're all done
    report_queue.put(None)
    thread.join()
    report_queue.join()


def process_file(file_name, report_queue):
    enqueued = False
    try:
        if os.path.getsize(file_name) == 0:
            return
        log.info('Analyzing %s', file_name)
        with open(get_analyzing_now_path(), 'w') as analyzing:
            analyzing.write(file_name)
        file = ParseFileName(file_name)
        detections = run_analysis(file)
        # The queue is bounded (maxsize=1), so this blocks only if reporting is a
        # full chunk behind - same guarantee the old join() gave, but the next
        # chunk's inference can overlap this chunk's reporting.
        report_queue.put((file, detections))
        enqueued = True
    except Exception as e:
        stderr = e.stderr.decode('utf-8') if isinstance(e, CalledProcessError) else ""
        log.exception(f'Unexpected error: {stderr}', exc_info=e)
    finally:
        # On success the reporting thread owns the file and removes it there.
        # Only clean up here when we failed before handing it off - otherwise a
        # failed analysis strands the wav forever (nothing else reaps StreamData).
        if not enqueued:
            try:
                os.remove(file_name)
            except OSError:
                pass


def handle_reporting_queue(queue):
    while True:
        msg = queue.get()
        # check for signal that we are done
        if msg is None:
            break

        file, detections = msg
        try:
            update_json_file(file, detections)
            reported = []
            for detection in detections:
                # Contain per detection: write_to_db now raises on persistent
                # failure, and without this one bad row would drop every later
                # detection in the chunk AND skip apprise/bird_weather/heartbeat
                # below - a wider desync than the silent drop it replaced, and a
                # missed heartbeat can trip a false "station down" alert.
                try:
                    detection.file_name_extr = extract_detection(file, detection)
                    log.info('%s;%s', summary(file, detection), os.path.basename(detection.file_name_extr))
                    write_to_file(file, detection)
                    write_to_db(file, detection)
                    reported.append(detection)
                except Exception as e:
                    log.exception('dropping detection %s', detection.common_name, exc_info=e)
            # Only pass on detections that actually made it: apprise() and
            # bird_weather() read detection.file_name_extr, which is unset if
            # extract_detection() was the thing that failed.
            if reported:
                apprise(file, reported)
                bird_weather(file, reported)
            heartbeat()
        except Exception as e:
            stderr = e.stderr.decode('utf-8') if isinstance(e, CalledProcessError) else ""
            log.exception(f'Unexpected error: {stderr}', exc_info=e)
        finally:
            # This is the ONLY place StreamData wavs get removed (cleanup.sh only
            # reaps PROCESSED), so it must run even when reporting above fails -
            # otherwise any error strands the wav permanently.
            try:
                os.remove(file.file_name)
            except OSError:
                pass
            queue.task_done()

    # mark the 'None' signal as processed
    queue.task_done()
    log.info('handle_reporting_queue done')


def setup_logging():
    logger = logging.getLogger()
    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    global log
    log = logging.getLogger('birdnet_analysis')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    setup_logging()

    main()
