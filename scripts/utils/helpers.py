import glob
import json
import os
import re
import subprocess
from collections import OrderedDict
from configparser import ConfigParser
from itertools import chain

_settings = None

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(BASE_PATH, 'scripts/birds.db')
MODEL_PATH = os.path.join(BASE_PATH, 'model')
FONT_DIR = os.path.join(BASE_PATH, 'frontend/static/fonts')
ANALYZING_NOW = os.path.expanduser('~/BirdSongs/StreamData/analyzing_now.txt')
FALLBACK_FONT_DIRS = (
    FONT_DIR,
    os.path.join(BASE_PATH, 'homepage/static'),
    '/usr/share/fonts/truetype/dejavu',
    '/usr/share/fonts/truetype/liberation2',
    '/usr/share/fonts/truetype/freefont',
)

# User-selectable classifier models. This excludes auxiliary metadata models.
USER_SELECTABLE_MODELS = (
    'BirdNET_GLOBAL_6K_V2.4_Model_FP16',
    'BirdNET_6K_GLOBAL_MODEL',
    'Perch_v2',
    'BirdNET-Go_classifier_20250916',
)
SPECIES_FILTER_MODELS = (
    'BirdNET_GLOBAL_6K_V2.4_Model_FP16',
    'BirdNET-Go_classifier_20250916',
)


def get_font():
    conf = get_settings()
    if conf['DATABASE_LANG'] == 'ar':
        ret = {'font.family': 'Noto Sans Arabic', 'path': os.path.join(FONT_DIR, 'NotoSansArabic-Regular.ttf')}
    elif conf['DATABASE_LANG'] in ['ja', 'zh_CN', 'zh_TW']:
        ret = {'font.family': 'Noto Sans JP', 'path': os.path.join(FONT_DIR, 'NotoSansJP-Regular.ttf')}
    elif conf['DATABASE_LANG'] == 'ko':
        ret = {'font.family': 'Noto Sans KR', 'path': os.path.join(FONT_DIR, 'NotoSansKR-Regular.ttf')}
    elif conf['DATABASE_LANG'] == 'th':
        ret = {'font.family': 'Noto Sans Thai', 'path': os.path.join(FONT_DIR, 'NotoSansThai-Regular.ttf')}
    else:
        ret = {'font.family': 'Roboto Flex', 'path': os.path.join(FONT_DIR, 'RobotoFlex-Regular.ttf')}

    if not os.path.isfile(ret['path']):
        font_file = os.path.basename(ret['path'])
        for font_dir in FALLBACK_FONT_DIRS:
            candidate = os.path.join(font_dir, font_file)
            if os.path.isfile(candidate):
                ret['path'] = candidate
                break
        else:
            for fallback_file in ('DejaVuSans.ttf', 'LiberationSans-Regular.ttf', 'FreeSans.ttf'):
                for font_dir in FALLBACK_FONT_DIRS:
                    candidate = os.path.join(font_dir, fallback_file)
                    if os.path.isfile(candidate):
                        ret['path'] = candidate
                        return ret
    return ret


class BirdNETConfigParser(ConfigParser):
    def get(self, section, option, *, raw=False, vars=None, fallback=None):
        value = super().get(section, option, raw=raw, vars=vars, fallback=fallback)
        if raw:
            return value
        else:
            return value.strip('"')


def _load_settings(settings_path='/etc/birdnet/birdnet.conf', force_reload=False):
    global _settings
    if _settings is None or force_reload:
        with open(settings_path) as f:
            parser = BirdNETConfigParser(interpolation=None)
            # preserve case
            parser.optionxform = lambda option: option
            lines = chain(("[top]",), f)
            parser.read_file(lines)
            _settings = parser['top']
    return _settings


def get_settings(settings_path='/etc/birdnet/birdnet.conf', force_reload=False):
    settings = _load_settings(settings_path, force_reload)
    return settings


def get_open_files_in_dir(dir_name):
    result = subprocess.run(['lsof', '-w', '-Fn', '+D', f'{dir_name}'], check=False, capture_output=True)
    ret = result.stdout.decode('utf-8')
    err = result.stderr.decode('utf-8')
    if err:
        raise RuntimeError(f'{ret}:\n {err}')
    names = [line.lstrip('n') for line in ret.splitlines() if line.startswith('n')]
    return names


def get_wav_files():
    conf = get_settings()
    files = (glob.glob(os.path.join(conf['RECS_DIR'], '*/*/*.wav')) +
             glob.glob(os.path.join(conf['RECS_DIR'], 'StreamData/*.wav')))
    files.sort()
    files = [os.path.join(conf['RECS_DIR'], file) for file in files]
    rec_dir = os.path.join(conf['RECS_DIR'], 'StreamData')
    open_recs = get_open_files_in_dir(rec_dir)
    files = [file for file in files if file not in open_recs]
    return files


def get_language(language=None):
    if language is None:
        language = get_settings()['DATABASE_LANG']
    file_name = os.path.join(MODEL_PATH, f'l18n/labels_{language}.json')
    with open(file_name) as f:
        ret = json.loads(f.read())
    return ret


def save_language(labels, language):
    file_name = os.path.join(MODEL_PATH, f'l18n/labels_{language}.json')
    with open(file_name, 'w') as f:
        f.write(json.dumps(OrderedDict(sorted(labels.items())), indent=2, ensure_ascii=False))


def get_model_labels(model=None):
    if model is None:
        model = get_settings()['MODEL']
    file_name = os.path.join(MODEL_PATH, f'{model}_Labels.txt')
    with open(file_name) as f:
        labels = [line.strip() for line in f.readlines()]
    if labels and labels[0].count('_') == 1:
        labels = [re.sub(r'_.+$', '', label) for label in labels]
    return labels


def set_label_file():
    lang = get_language()
    labels = [f'{label}_{lang[label]}\n' for label in get_model_labels()]
    file_name = os.path.join(MODEL_PATH, 'labels.txt')
    if os.path.islink(file_name):
        os.remove(file_name)
    with open(file_name, 'w') as f:
        f.writelines(labels)


def list_installed_selectable_models():
    models = []
    for model_name in USER_SELECTABLE_MODELS:
        model_path = os.path.join(MODEL_PATH, f'{model_name}.tflite')
        labels_path = os.path.join(MODEL_PATH, f'{model_name}_Labels.txt')
        if os.path.exists(model_path) and os.path.exists(labels_path):
            models.append(model_name)
    return models


def model_supports_species_filter(model_name):
    return model_name in SPECIES_FILTER_MODELS
