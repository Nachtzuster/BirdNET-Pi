import logging
import math
import operator
import os
import time

import librosa
import numpy as np

from utils.helpers import get_settings, Detection

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

try:
    import tflite_runtime.interpreter as tflite
except BaseException:
    from tensorflow import lite as tflite

log = logging.getLogger(__name__)


userDir = os.path.expanduser('~')
INTERPRETER, M_INTERPRETER, INCLUDE_LIST, EXCLUDE_LIST = (None, None, None, None)
PREDICTED_SPECIES_LIST = []
WEEK = None
model, sf_thresh = (None, None)

mdata, mdata_params = (None, None)


def loadModel():

    global INPUT_LAYER_INDEX
    global OUTPUT_LAYER_INDEX
    global MDATA_INPUT_INDEX
    global CLASSES

    log.info('LOADING TF LITE MODEL...')

    # Load TFLite model and allocate tensors.
    # model will either be BirdNET_GLOBAL_6K_V2.4_Model_FP16 (new) or BirdNET_6K_GLOBAL_MODEL (old)
    modelpath = userDir + '/BirdNET-Pi/model/'+model+'.tflite'
    myinterpreter = tflite.Interpreter(model_path=modelpath, num_threads=2)
    myinterpreter.allocate_tensors()

    # Get input and output tensors.
    input_details = myinterpreter.get_input_details()
    output_details = myinterpreter.get_output_details()

    # Get input tensor index
    INPUT_LAYER_INDEX = input_details[0]['index']
    if model == "BirdNET_6K_GLOBAL_MODEL":
        MDATA_INPUT_INDEX = input_details[1]['index']
    OUTPUT_LAYER_INDEX = output_details[0]['index']

    # Load labels
    CLASSES = []
    labelspath = userDir + '/BirdNET-Pi/model/labels.txt'
    with open(labelspath, 'r') as lfile:
        for line in lfile.readlines():
            CLASSES.append(line.replace('\n', ''))

    log.info('LOADING DONE!')

    return myinterpreter


def loadMetaModel():

    global M_INTERPRETER
    global M_INPUT_LAYER_INDEX
    global M_OUTPUT_LAYER_INDEX

    if get_settings().getint('DATA_MODEL_VERSION') == 2:
        data_model = 'BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite'
    else:
        data_model = 'BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite'

    # Load TFLite model and allocate tensors.
    M_INTERPRETER = tflite.Interpreter(model_path=os.path.join(userDir, 'BirdNET-Pi/model', data_model))
    M_INTERPRETER.allocate_tensors()

    # Get input and output tensors.
    input_details = M_INTERPRETER.get_input_details()
    output_details = M_INTERPRETER.get_output_details()

    # Get input tensor index
    M_INPUT_LAYER_INDEX = input_details[0]['index']
    M_OUTPUT_LAYER_INDEX = output_details[0]['index']

    log.info("loaded META model")


def predictFilter(lat, lon, week):
    # Does interpreter exist?
    if M_INTERPRETER is None:
        loadMetaModel()

    # Prepare mdata as sample
    sample = np.expand_dims(np.array([lat, lon, week], dtype='float32'), 0)

    # Run inference
    M_INTERPRETER.set_tensor(M_INPUT_LAYER_INDEX, sample)
    M_INTERPRETER.invoke()

    return M_INTERPRETER.get_tensor(M_OUTPUT_LAYER_INDEX)[0]


def explore(lat, lon, week):

    # Make filter prediction
    l_filter = predictFilter(lat, lon, week)

    # Apply threshold
    l_filter = np.where(l_filter >= float(sf_thresh), l_filter, 0)

    # Zip with labels
    l_filter = list(zip(l_filter, CLASSES))

    # Sort by filter value
    l_filter = sorted(l_filter, key=lambda x: x[0], reverse=True)

    return l_filter


def predictSpeciesList(lat, lon, week):

    l_filter = explore(lat, lon, week)
    for s in l_filter:
        if s[0] >= float(sf_thresh):
            # if there's a custom user-made include list, we only want to use the species in that
            if (len(INCLUDE_LIST) == 0):
                PREDICTED_SPECIES_LIST.append(s[1])


def loadCustomSpeciesList(path):

    slist = []
    if os.path.isfile(path):
        with open(path, 'r') as csfile:
            for line in csfile.readlines():
                slist.append(line.replace('\r', '').replace('\n', ''))

    return slist


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


def readAudioData(path, overlap, sample_rate=48000):

    log.info('READING AUDIO DATA...')

    # Open file with librosa (uses ffmpeg or libav)
    sig, rate = librosa.load(path, sr=sample_rate, mono=True, res_type='kaiser_fast')

    # Split audio into 3-second chunks
    chunks = splitSignal(sig, rate, overlap)

    log.info('READING DONE! READ %d CHUNKS.', len(chunks))

    return chunks


def convertMetadata(m):

    # Convert week to cosine
    if m[2] >= 1 and m[2] <= 48:
        m[2] = math.cos(math.radians(m[2] * 7.5)) + 1
    else:
        m[2] = -1

    # Add binary mask
    mask = np.ones((3,))
    if m[0] == -1 or m[1] == -1:
        mask = np.zeros((3,))
    if m[2] == -1:
        mask[2] = 0.0

    return np.concatenate([m, mask])


def custom_sigmoid(x, sensitivity=1.0):
    return 1 / (1.0 + np.exp(-sensitivity * x))


def predict(sample, sensitivity):
    # Make a prediction
    INTERPRETER.set_tensor(INPUT_LAYER_INDEX, np.array(sample[0], dtype='float32'))
    if model == "BirdNET_6K_GLOBAL_MODEL":
        INTERPRETER.set_tensor(MDATA_INPUT_INDEX, np.array(sample[1], dtype='float32'))
    INTERPRETER.invoke()
    prediction = INTERPRETER.get_tensor(OUTPUT_LAYER_INDEX)[0]

    # Apply custom sigmoid
    p_sigmoid = custom_sigmoid(prediction, sensitivity)

    # Get label and scores for pooled predictions
    p_labels = dict(zip(CLASSES, p_sigmoid))

    # Sort by score
    p_sorted = sorted(p_labels.items(), key=operator.itemgetter(1), reverse=True)

    return p_sorted


def analyzeAudioData(chunks, lat, lon, week, sens, overlap,):
    global WEEK

    sensitivity = max(0.5, min(1.0 - (sens - 1.0), 1.5))

    detections = []
    start = time.time()
    log.info('ANALYZING AUDIO...')

    if model == "BirdNET_GLOBAL_6K_V2.4_Model_FP16":
        if week != WEEK or len(INCLUDE_LIST) != 0:
            WEEK = week
            predictSpeciesList(lat, lon, week)

    mdata = get_metadata(lat, lon, week)

    # Parse every chunk
    for c in chunks:
        # Prepare as input signal
        sig = np.expand_dims(c, 0)

        # Make prediction
        p = predict([sig, mdata], sensitivity)
        log.debug("PPPPP: %s", p)
        detections.append(p)

    labeled = {}
    pred_start = 0.0
    for p in filter_humans(detections):
        # Save timestamp and result
        pred_end = pred_start + 3.0
        labeled[str(pred_start) + ';' + str(pred_end)] = p

        pred_start = pred_end - overlap

    log.info('DONE! Time %.2f SECONDS', time.time() - start)
    return labeled


def filter_humans(detections):
    conf = get_settings()
    priv_thresh = conf.getfloat('PRIVACY_THRESHOLD')
    human_cutoff = max(10, int(len(detections[0]) * priv_thresh / 100.0))
    log.debug("DATABASE SIZE: %d", len(detections[0]))
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


def get_metadata(lat, lon, week):
    global mdata, mdata_params
    if mdata_params != [lat, lon, week]:
        mdata_params = [lat, lon, week]
        # Convert and prepare metadata
        mdata = convertMetadata(np.array([lat, lon, week]))
        mdata = np.expand_dims(mdata, 0)

    return mdata


def load_global_model():
    global INTERPRETER
    global model, sf_thresh
    conf = get_settings()
    model = conf['MODEL']
    sf_thresh = conf.getfloat('SF_THRESH')
    INTERPRETER = loadModel()


def run_analysis(file):
    global INCLUDE_LIST, EXCLUDE_LIST, WHITELIST_LIST
    INCLUDE_LIST = loadCustomSpeciesList(os.path.expanduser("~/BirdNET-Pi/include_species_list.txt"))
    EXCLUDE_LIST = loadCustomSpeciesList(os.path.expanduser("~/BirdNET-Pi/exclude_species_list.txt"))
    WHITELIST_LIST = loadCustomSpeciesList(os.path.expanduser("~/BirdNET-Pi/whitelist_species_list.txt"))

    conf = get_settings()

    # Read audio data & handle errors
    try:
        audio_data = readAudioData(file.file_name, conf.getfloat('OVERLAP'))
    except (NameError, TypeError) as e:
        log.error("Error with the following info: %s", e)
        return []

    # Process audio data and get detections
    raw_detections = analyzeAudioData(audio_data, conf.getfloat('LATITUDE'), conf.getfloat('LONGITUDE'), file.week,
                                      conf.getfloat('SENSITIVITY'), conf.getfloat('OVERLAP'))
    confident_detections = []
    for time_slot, entries in raw_detections.items():
        log.info('%s-%s', time_slot, entries[0])
        for entry in entries:
            if entry[1] >= conf.getfloat('CONFIDENCE'):
                if entry[0] not in INCLUDE_LIST and len(INCLUDE_LIST) != 0:
                    log.warning("Excluded as INCLUDE_LIST is active but this species is not in it: %s", entry[0])
                elif entry[0] in EXCLUDE_LIST and len(EXCLUDE_LIST) != 0:
                    log.warning("Excluded as species in EXCLUDE_LIST: %s", entry[0])
                elif entry[0] not in PREDICTED_SPECIES_LIST and len(PREDICTED_SPECIES_LIST) != 0 and entry[0] not in WHITELIST_LIST:
                    log.warning("Excluded as below Species Occurrence Frequency Threshold: %s", entry[0])
                else:
                    d = Detection(
                        file.file_date,
                        time_slot.split(';')[0],
                        time_slot.split(';')[1],
                        entry[0],
                        entry[1],
                    )
                    confident_detections.append(d)
    return confident_detections
