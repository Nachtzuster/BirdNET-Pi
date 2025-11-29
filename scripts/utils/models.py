import logging
import math
import operator
import os
import tarfile

import numpy as np
import requests

from .helpers import get_settings, get_model_labels, MODEL_PATH

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
np.set_printoptions(legacy="1.21")

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    from tensorflow import lite as tflite

log = logging.getLogger(__name__)


def get_model(model=None):
    conf = get_settings()
    if model is None:
        model = conf['MODEL']

    if model == 'BirdNET_6K_GLOBAL_MODEL':
        return BirdNetV1(conf.getfloat('SENSITIVITY'))
    elif model == 'BirdNET_GLOBAL_6K_V2.4_Model_FP16':
        return BirdNetV2_4(conf.getfloat('SENSITIVITY'))
    elif model == 'Perch_v2':
        return Perch()
    elif model == 'BirdNET-Go_classifier_20250916':
        return BirdNETGo20250916(conf.getfloat('SENSITIVITY'))


def get_meta_model(model=None, version=None):
    conf = get_settings()
    if model is None:
        model = conf['MODEL']
    if version is None:
        version = conf.getint('DATA_MODEL_VERSION')

    if model not in ['BirdNET_GLOBAL_6K_V2.4_Model_FP16', 'BirdNET-Go_classifier_20250916']:
        return None

    if version == 1:
        return MDataModel1(conf.getfloat('SF_THRESH'))
    elif version == 2:
        return MDataModel2(conf.getfloat('SF_THRESH'))


def download_file(url, file_path):
    tmp_file = f"{file_path}_tmp"
    session = requests.Session()
    response = session.get(url, stream=True)
    response.raise_for_status()
    block_size = 32768

    log.info('Downloading: %s' % os.path.basename(file_path))
    downloaded_size = 0
    try:
        with open(tmp_file, "wb") as outfile:
            for data in response.iter_content(block_size):
                downloaded_size += len(data)
                log.info(f'Progress: {downloaded_size}')
                outfile.write(data)
    except requests.exceptions.HTTPError as e:
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)
        raise e

    os.rename(tmp_file, file_path)


class Basemodel:
    chunk_duration = None
    sample_rate = None
    model_name = None
    _input_layer = 0
    _output_layer = 0

    def __init__(self):
        self.model_path = os.path.join(MODEL_PATH, f'{self.model_name}.tflite')
        self.ensure_model()
        self.interpreter = tflite.Interpreter(self.model_path)
        self.interpreter.allocate_tensors()
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()

        self._input_layer_idx = input_details[self._input_layer]['index']
        self._output_layer_idx = output_details[self._output_layer]['index']

        self.labels = get_model_labels(self.model_name)

    def label(self, logits):
        p_labels = dict(zip(self.labels, logits))
        return sorted(p_labels.items(), key=operator.itemgetter(1), reverse=True)

    def predict(self, chunk):
        raise NotImplementedError

    def set_meta_data(self, lat, lon, week):
        pass

    def get_species_list(self):
        return []

    def ensure_model(self):
        pass


class BirdNet(Basemodel):
    chunk_duration = 3
    sample_rate = 48000

    def __init__(self, sens):
        super().__init__()

        self._mdata_model = self._set_meta_model()

        self._sensitivity = max(0.5, min(1.0 - (sens - 1.0), 1.5))

    def scale(self, logits):
        return 1 / (1.0 + np.exp(-self._sensitivity * logits))

    def _set_meta_model(self):
        return None


class BirdNetV1(BirdNet):
    model_name = 'BirdNET_6K_GLOBAL_MODEL'

    def __init__(self, sens):
        super().__init__(sens)
        self._mdata = None
        self._mdata_params = None

    def _set_meta_model(self):
        input_details = self.interpreter.get_input_details()
        return input_details[1]['index']

    def predict(self, chunk):
        self.interpreter.set_tensor(self._input_layer_idx, np.array(chunk, dtype='float32')[np.newaxis, :])
        self.interpreter.set_tensor(self._mdata_model, np.array(self._mdata, dtype='float32'))

        self.interpreter.invoke()
        logits = self.interpreter.get_tensor(self._output_layer_idx)[0]

        return self.label(self.scale(logits))

    def _convert_metadata(self, m):
        # Convert week to cosine
        if 1 <= m[2] <= 48:
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

    def set_meta_data(self, lat, lon, week):
        if self._mdata_params != [lat, lon, week]:
            self._mdata_params = [lat, lon, week]
            # Convert and prepare metadata
            mdata = self._convert_metadata(np.array([lat, lon, week]))
            self._mdata = np.expand_dims(mdata, 0)


class BirdNetV2_4(BirdNet):
    model_name = 'BirdNET_GLOBAL_6K_V2.4_Model_FP16'

    def _set_meta_model(self):
        return get_meta_model()

    def predict(self, chunk):
        self.interpreter.set_tensor(self._input_layer_idx, np.array(chunk, dtype='float32')[np.newaxis, :])

        self.interpreter.invoke()
        logits = self.interpreter.get_tensor(self._output_layer_idx)[0]

        return self.label(self.scale(logits))

    def set_meta_data(self, lat, lon, week):
        self._mdata_model.set_meta_data(lat, lon, week)

    def get_species_list(self):
        return self._mdata_model.get_species_list(self.labels)


class Perch(Basemodel):
    chunk_duration = 5
    sample_rate = 32000
    model_name = 'Perch_v2'
    _output_layer = 3

    def predict(self, chunk):
        self.interpreter.set_tensor(self._input_layer_idx, np.array(chunk, dtype='float32')[np.newaxis, :])

        self.interpreter.invoke()
        logits = self.interpreter.get_tensor(self._output_layer_idx)[0]

        exp_x = np.exp(logits - np.max(logits))  # Stabilizing to prevent overflow
        return self.label(exp_x / np.sum(exp_x))

    def ensure_model(self):
        if os.path.exists(self.model_path):
            return
        base_url = 'https://github.com/Nachtzuster/BirdNET-Pi/releases/download/v0.11'
        file = 'Perch_v2.tar.gz'
        tmp_file = os.path.join(MODEL_PATH, file)
        download_file(f'{base_url}/{file}', tmp_file)
        log.info(f'Extracting {file}...')
        with tarfile.open(tmp_file, "r:gz") as tar:
            tar.extractall(MODEL_PATH)
        os.unlink(tmp_file)


class BirdNETGo20250916(BirdNetV2_4):
    model_name = 'BirdNET-Go_classifier_20250916'

    def ensure_model(self):
        if os.path.exists(self.model_path):
            return
        base_url = 'https://raw.githubusercontent.com/tphakala/birdnet-go-classifiers/refs/heads/main/20250916'
        for file in ['BirdNET-Go_classifier_20250916_Labels.txt', 'BirdNET-Go_classifier_20250916.tflite']:
            download_file(f'{base_url}/{file}', os.path.join(MODEL_PATH, file))


class MDataModel:
    model_name = None

    def __init__(self, sf_thresh):
        model_path = os.path.join(MODEL_PATH, f'{self.model_name}.tflite')
        self.interpreter = tflite.Interpreter(model_path)
        self.interpreter.allocate_tensors()
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()

        self._input_layer_idx = input_details[0]['index']
        self._output_layer_idx = output_details[0]['index']
        self._sf_thresh = sf_thresh

        self._mdata_params = None
        self._mdata = None

    def set_meta_data(self, lat, lon, week):
        if self._mdata_params != (lat, lon, week):
            self._mdata = None
        self._mdata_params = (lat, lon, week)

    def get_species_list_details(self, labels):
        if self._mdata is None:
            lat, lon, week = self._mdata_params
            sample = np.expand_dims(np.array([lat, lon, week], dtype='float32'), 0)

            # Run inference
            self.interpreter.set_tensor(self._input_layer_idx, sample)
            self.interpreter.invoke()

            l_filter = self.interpreter.get_tensor(self._output_layer_idx)[0]

            # Apply threshold
            l_filter = np.where(l_filter >= float(self._sf_thresh), l_filter, 0)

            # Zip with labels
            l_filter = list(zip(l_filter, labels))

            # Sort by filter value
            l_filter = sorted(l_filter, key=lambda x: x[0], reverse=True)

            self._mdata = [s for s in l_filter if s[0] >= self._sf_thresh]

        return self._mdata

    def get_species_list(self, labels):
        l_filter = self.get_species_list_details(labels)
        return [s[1].split('_')[0] for s in l_filter]


class MDataModel1(MDataModel):
    model_name = 'BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16'


class MDataModel2(MDataModel):
    model_name = 'BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16'
