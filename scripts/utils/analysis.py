import logging
import os
import time

import librosa
import numpy as np

from .classes import Detection, ParseFileName
from .helpers import get_settings, get_language
from .models import get_model

log = logging.getLogger(__name__)

MODEL = None


def loadCustomSpeciesList(path):
    species_list = []
    if os.path.isfile(path):
        with open(path, 'r') as csfile:
            species_list = [line.strip().split('_')[0] for line in csfile.readlines()]

    return species_list


def splitSignal(sig, rate, overlap, seconds=3.0, minlen=1.5):
    # Split signal with overlap
    sig_splits = []
    for i in range(0, len(sig), int((seconds - overlap) * rate)):
        split = sig[i:i + int(seconds * rate)]

        # End of signal?
        if len(split) < int(minlen * rate):
            break

        # Signal chunk too short? Fill with zeros.
        if len(split) < int(rate * seconds):
            temp = np.zeros((int(rate * seconds)))
            temp[:len(split)] = split
            split = temp

        sig_splits.append(split)

    return sig_splits


def readAudioData(path, overlap, sample_rate, chunk_duration):
    log.info('READING AUDIO DATA...')

    # Open file with librosa (uses ffmpeg or libav)
    sig, rate = librosa.load(path, sr=sample_rate, mono=True, res_type='kaiser_fast')

    # Split audio into chunks
    chunks = splitSignal(sig, rate, overlap, seconds=chunk_duration)

    log.info('READING DONE! READ %d CHUNKS.', len(chunks))

    return chunks


def analyzeAudioData(chunks, overlap, lat, lon, week):
    detections = []
    model = load_global_model()

    start = time.time()
    log.info('ANALYZING AUDIO...')

    model.set_meta_data(lat, lon, week)
    predicted_species_list = model.get_species_list()

    # Parse every chunk
    for chunk in chunks:
        p = model.predict(chunk)
        log.debug("PPPPP: %s", p)
        detections.append(p)

    labeled = {}
    pred_start = 0.0
    for p in filter_humans(detections):
        # Save timestamp and result
        pred_end = pred_start + model.chunk_duration
        labeled[str(pred_start) + ';' + str(pred_end)] = p

        pred_start = pred_end - overlap

    log.info('DONE! Time %.2f SECONDS', time.time() - start)
    return labeled, predicted_species_list


def filter_humans(detections):
    conf = get_settings()
    priv_thresh = conf.getfloat('PRIVACY_THRESHOLD')
    human_cutoff = max(10, int(6000 * priv_thresh / 100.0))
    log.debug("HUMAN-CUTOFF AT: %d", human_cutoff)

    censored_detections = []
    for detection in detections:
        p = detection[:human_cutoff]
        human_detected = False
        # Catch if Human is recognized in any of the predictions
        for x in p:
            if 'Human' in x[0]:
                human_detected = True

        # If human detected set detection to human to make sure voices are not saved
        if human_detected is True:
            p = [('Human_Human', 0.0)]
        else:
            p = p[:10]

        censored_detections.append(p)

    # now overwrite detections that have a human neighbour too
    try:
        extraction_length = conf.getint('EXTRACTION_LENGTH')
    except ValueError:
        extraction_length = 6
    if extraction_length > 9:
        log.warning("EXTRACTION_LENGTH is set to %d. Privacy filter might miss human sound, "
                    "if you care about privacy, set EXTRACTION_LENGTH to below 9 or leave empty.", extraction_length)
    human_neighbour_mask = [False] * len(censored_detections)
    for i, detection in enumerate(censored_detections):
        if i != 0:
            if censored_detections[i - 1][0][0] == 'Human_Human':
                human_neighbour_mask[i] = True
        if i != len(censored_detections) - 1:
            if censored_detections[i + 1][0][0] == 'Human_Human':
                human_neighbour_mask[i] = True

    clean_detections = []
    for i, (has_human_neighbour, detection) in enumerate(zip(human_neighbour_mask, censored_detections)):
        if has_human_neighbour and detection[0][0] != 'Human_Human':
            log.debug('Overwriting detection %d %s - Has Human neighbour', i + 1, detection[0])
            detection = [('Human_Human', 0.0)]
        clean_detections.append(detection)

    return clean_detections


def load_global_model():
    global MODEL
    if MODEL is None:
        log.info('LOADING TF LITE MODEL...')
        MODEL = get_model()
        log.info('LOADING DONE!')

    return MODEL


def run_analysis(file):
    include_list = loadCustomSpeciesList(os.path.expanduser("~/BirdNET-Pi/include_species_list.txt"))
    exclude_list = loadCustomSpeciesList(os.path.expanduser("~/BirdNET-Pi/exclude_species_list.txt"))
    whitelist_list = loadCustomSpeciesList(os.path.expanduser("~/BirdNET-Pi/whitelist_species_list.txt"))

    conf = get_settings()
    model = load_global_model()
    names = get_language(conf['DATABASE_LANG'])

    # Read audio data & handle errors
    try:
        audio_data = readAudioData(file.file_name, conf.getfloat('OVERLAP'), model.sample_rate, model.chunk_duration)
    except (NameError, TypeError) as e:
        log.error("Error with the following info: %s", e)
        return []

    # Process audio data and get detections
    raw_detections, predicted_species_list = analyzeAudioData(audio_data, conf.getfloat('OVERLAP'), conf.getfloat('LATITUDE'),
                                                              conf.getfloat('LONGITUDE'), file.week)
    confident_detections = []
    for time_slot, entries in raw_detections.items():
        sci_name, confidence = entries[0]
        log.info('%s-(%s_%s, %s)', time_slot, sci_name, names.get(sci_name, sci_name), confidence)
        for sci_name, confidence in entries:
            if confidence >= conf.getfloat('CONFIDENCE'):
                com_name = names.get(sci_name, sci_name)
                if sci_name not in include_list and len(include_list) != 0:
                    log.warning("Excluded as INCLUDE_LIST is active but this species is not in it: %s %s", sci_name, com_name)
                elif sci_name in exclude_list and len(exclude_list) != 0:
                    log.warning("Excluded as species in EXCLUDE_LIST: %s %s", sci_name, com_name)
                elif sci_name not in predicted_species_list and len(predicted_species_list) != 0 and sci_name not in whitelist_list:
                    log.warning("Excluded as below Species Occurrence Frequency Threshold: %s %s", sci_name, com_name)
                else:
                    d = Detection(
                        file.file_date,
                        time_slot.split(';')[0],
                        time_slot.split(';')[1],
                        sci_name,
                        com_name,
                        confidence,
                    )
                    confident_detections.append(d)
    return confident_detections


if __name__ == '__main__':
    conf = get_settings()
    model = conf['MODEL']
    test_files = ['../tests/testdata/2024-02-24-birdnet-16:19:37.wav']
    results = [{
        "BirdNET_6K_GLOBAL_MODEL": [
            {"confidence": 0.9894, 'sci_name': 'Pica pica'},
            {"confidence": 0.9779, 'sci_name': 'Pica pica'},
            {"confidence": 0.9943, 'sci_name': 'Pica pica'}],
        "BirdNET_GLOBAL_6K_V2.4_Model_FP16": [
            {"confidence": 0.912, 'sci_name': 'Pica pica'},
            {"confidence": 0.9316, 'sci_name': 'Pica pica'},
            {"confidence": 0.8857, 'sci_name': 'Pica pica'}],
        "Perch_v2": [
            {"confidence": 0.9641, 'sci_name': 'Pica pica'},
            {"confidence": 0.9609, 'sci_name': 'Pica pica'},
            {"confidence": 0.9468, 'sci_name': 'Pica pica'}],
        "BirdNET-Go_classifier_20250916": [
            {"confidence": 0.9123, 'sci_name': 'Pica pica'},
            {"confidence": 0.9317, 'sci_name': 'Pica pica'},
            {"confidence": 0.8861, 'sci_name': 'Pica pica'}],
    }]

    for sample, expected in zip(test_files, results):
        file = ParseFileName(os.path.expanduser(sample))
        detections = run_analysis(file)
        assert (len(detections) == len(expected[model]))
        for det, this_det in zip(detections, expected[model]):
            assert (det.confidence == this_det['confidence'])
            assert (det.scientific_name == this_det['sci_name'])
    print('ok')
