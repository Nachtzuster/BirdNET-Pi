import glob
import json
import os
import subprocess
from collections import OrderedDict
from configparser import ConfigParser
from itertools import chain

_settings = None

DB_PATH = os.path.expanduser('~/BirdNET-Pi/scripts/birds.db')
MODEL_PATH = os.path.expanduser('~/BirdNET-Pi/model')
ANALYZING_NOW = os.path.expanduser('~/BirdSongs/StreamData/analyzing_now.txt')
FONT_DIR = os.path.expanduser('~/BirdNET-Pi/homepage/static')


def get_font():
    conf = get_settings()
    if conf['DATABASE_LANG'] == 'ar':
        ret = {'font.family': 'Noto Sans Arabic', 'path': os.path.join(FONT_DIR, 'NotoSansArabic-Regular.ttf')}
    elif conf['DATABASE_LANG'] in ['ja', 'zh']:
        ret = {'font.family': 'Noto Sans JP', 'path': os.path.join(FONT_DIR, 'NotoSansJP-Regular.ttf')}
    elif conf['DATABASE_LANG'] == 'ko':
        ret = {'font.family': 'Noto Sans KR', 'path': os.path.join(FONT_DIR, 'NotoSansKR-Regular.ttf')}
    elif conf['DATABASE_LANG'] == 'th':
        ret = {'font.family': 'Noto Sans Thai', 'path': os.path.join(FONT_DIR, 'NotoSansThai-Regular.ttf')}
    else:
        ret = {'font.family': 'Roboto Flex', 'path': os.path.join(FONT_DIR, 'RobotoFlex-Regular.ttf')}
    return ret


class PHPConfigParser(ConfigParser):
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
            parser = PHPConfigParser(interpolation=None)
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
        ret = [line.strip() for line in f.readlines()]
    return ret


def set_label_file():
    lang = get_language()
    labels = [f'{label}_{lang[label]}\n' for label in get_model_labels()]
    file_name = os.path.join(MODEL_PATH, 'labels.txt')
    if os.path.islink(file_name):
        os.remove(file_name)
    with open(file_name, 'w') as f:
        f.writelines(labels)


def get_labels(model, language=None):
    postfix = '' if language is None else f'_{language}'
    file_name = os.path.join(MODEL_PATH, f'labels_{model}/labels{postfix}.txt')
    with open(file_name) as f:
        ret = [line.strip() for line in f.readlines()]
    return ret


def as_dict(labels, den="_", key=0, value=1):
    return {label.split(den)[key]: label.split(den)[value] for label in labels}


def create_language(language):
    en_l18n = as_dict(get_labels('l18n', 'en'))
    l18n = as_dict(get_labels('l18n', language))
    new_language = as_dict(get_labels('nm', language))

    for sci_name, com_name in l18n.items():
        if sci_name not in new_language or new_language[sci_name] == sci_name:
            new_language[sci_name] = com_name
            continue

        # now check if the l18n version is translated
        if com_name != new_language[sci_name] and new_language[sci_name] == en_l18n[sci_name]:
            print(f'changing {new_language[sci_name]} -> {com_name}')
            new_language[sci_name] = com_name

    save_language(new_language, language)


def create_all_languages():
    languages = ['af', 'ar', 'ca', 'cs', 'da', 'de', 'en', 'es', 'et', 'fi', 'fr', 'hr', 'hu', 'id', 'is', 'it', 'ja',
                 'ko', 'lt', 'lv', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sr', 'sv', 'th', 'tr', 'uk', 'zh']
    for language in languages:
        create_language(language)
