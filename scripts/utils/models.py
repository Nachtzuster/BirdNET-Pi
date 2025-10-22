import logging
import math
import operator
import os

import numpy as np

from .helpers import get_settings

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
np.set_printoptions(legacy="1.21")

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    from tensorflow import lite as tflite

log = logging.getLogger(__name__)

_model_path = '~/BirdNET-Pi/model/'


def get_model(model=None):
    conf = get_settings()
    if model is None:
        model = conf['MODEL']

    if model == 'BirdNET_6K_GLOBAL_MODEL':
        return BirdNetV1(conf.getfloat('SENSITIVITY'))
    elif model == 'BirdNET_GLOBAL_6K_V2.4_Model_FP16':
        return BirdNetV2_4(conf.getfloat('SENSITIVITY'))


def get_meta_model(model=None, version=None):
    conf = get_settings()
    if model is None:
        model = conf['MODEL']
    if version is None:
        version = conf.getint('DATA_MODEL_VERSION')

    if model != 'BirdNET_GLOBAL_6K_V2.4_Model_FP16':
        return MDataModel0()

    if version == 1:
        return MDataModel1(conf.getfloat('SF_THRESH'))
    elif version == 2:
        return MDataModel2(conf.getfloat('SF_THRESH'))


class Basemodel:
    chunk_duration = None
    sample_rate = None
    _model_name = None
    _input_layer = 0
    _output_layer = 0

    def __init__(self):
        model_path = os.path.expanduser(os.path.join(_model_path, self._model_name))
        self.interpreter = tflite.Interpreter(model_path)
        self.interpreter.allocate_tensors()
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()

        self._input_layer_idx = input_details[self._input_layer]['index']
        self._output_layer_idx = output_details[self._output_layer]['index']

        self.labels = self.load_labels()

    def load_labels(self):
        model_name = os.path.splitext(self._model_name)[0]
        label_path = os.path.expanduser(os.path.join(_model_path, f'{model_name}_Labels.txt'))
        with open(label_path, 'r') as lfile:
            return [line.strip() for line in lfile.readlines()]

    def label(self, logits):
        p_labels = dict(zip(self.labels, logits))
        return sorted(p_labels.items(), key=operator.itemgetter(1), reverse=True)

    def predict(self, chunk):
        pass

    def set_meta_data(self, lat, lon, week):
        pass

    def get_species_list(self):
        return []


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
    _model_name = 'BirdNET_6K_GLOBAL_MODEL.tflite'

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
    _model_name = 'BirdNET_GLOBAL_6K_V2.4_Model_FP16.tflite'

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


class MDataModel0:
    def set_meta_data(self, lat, lon, week):
        pass

    def get_species_list(self, labels):
        return []


class MDataModel(MDataModel0):
    _model_name = None

    def __init__(self, sf_thresh):
        model_path = os.path.expanduser(os.path.join(_model_path, self._model_name))
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
    _model_name = 'BirdNET_GLOBAL_6K_V2.4_MData_Model_FP16.tflite'


class MDataModel2(MDataModel):
    _model_name = 'BirdNET_GLOBAL_6K_V2.4_MData_Model_V2_FP16.tflite'
