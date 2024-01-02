import os.path
import re
import signal
import threading
import traceback
from queue import Queue

import inotify.adapters
from inotify.constants import IN_CLOSE_WRITE

from server import load_global_model, run_analysis
from utils.helpers import get_settings, ParseFileName, get_wav_files, write_settings
from utils.reporting import report_all

shutdown = False


def sig_handler(sig_num, curr_stack_frame):
    global shutdown
    print(f'Caught shutdown signal {sig_num}')
    shutdown = True


def main():
    write_settings()
    load_global_model()
    conf = get_settings()
    i = inotify.adapters.Inotify()
    i.add_watch(os.path.join(conf['RECS_DIR'], 'StreamData'), mask=IN_CLOSE_WRITE)

    backlog = get_wav_files()

    report_queue = Queue()
    thread = threading.Thread(target=handle_reporting_queue, args=(report_queue, ))
    thread.start()

    print(f'backlog is {len(backlog)}')
    for file_name in backlog:
        process_file(file_name, report_queue)
        if shutdown:
            break
    print('backlog done')

    empty_count = 0
    for event in i.event_gen():
        if shutdown:
            break

        if event is None:
            if empty_count > (conf.getint('RECORDING_LENGTH') * 2):
                print('no more notifications: restarting...')
                break
            empty_count += 1
            continue

        (_, _, path, file_name) = event
        if re.search('.wav$', file_name) is None:
            continue
        # print("PATH=[{}] FILENAME=[{}] EVENT_TYPES={}".format(path, file_name, type_names))

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
    try:
        if os.path.getsize(file_name) == 0:
            os.remove(file_name)
            return
        print(f'Analyzing {file_name}')
        file = ParseFileName(file_name)
        detections = run_analysis(file)
        # we join() to make sure te reporting queue does not get behind
        report_queue.join()
        report_queue.put((file, detections))
    except BaseException:
        print(traceback.format_exc())


def handle_reporting_queue(queue):
    while True:
        msg = queue.get()
        # check for signal that we are done
        if msg is None:
            break

        file, detections = msg
        try:
            report_all(file, detections)
            os.remove(file.file_name)
        except BaseException:
            print(traceback.format_exc())

        queue.task_done()

    # mark the 'None' signal as processed
    queue.task_done()
    print('handle_reporting_queue done')


if __name__ == '__main__':
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    main()
