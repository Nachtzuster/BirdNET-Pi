import os
import re
import time
import requests

from .helpers import MODEL_PATH, save_language, get_language

key_lang = {'af': 'Afrikaans', 'ar': 'Arabic', 'ca': 'Catalan', 'cs': 'Czech', 'da': 'Danish', 'de': 'German', 'en': 'English', 'es': 'Spanish',
            'et': 'Estonian', 'fi': 'Finnish', 'fr': 'French', 'hr': 'Croatian', 'hu': 'Hungarian', 'id': 'Indonesian', 'is': 'Icelandic', 'it': 'Italian',
            'ja': 'Japanese', 'ko': 'Korean', 'lt': 'Lithuanian', 'lv': 'Latvian', 'nl': 'Dutch', 'no': 'Norwegian', 'pl': 'Polish', 'pt': 'Portuguese',
            'ro': 'Romanian', 'ru': 'Russian', 'sk': 'Slovak', 'sl': 'Slovenian', 'sr': 'Serbian', 'sv': 'Swedish', 'th': 'Thai', 'tr': 'Turkish',
            'uk': 'Ukrainian', 'vi': 'Vietnamese', 'zh_CN': 'Chinese (simplified)', 'zh_TW': 'Chinese (traditional)'}
languages = ['af', 'ar', 'ca', 'cs', 'da', 'de', 'en', 'es', 'et', 'fi', 'fr', 'hr', 'hu', 'id', 'is', 'it', 'ja',
             'ko', 'lt', 'lv', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl', 'sr', 'sv', 'th', 'tr', 'uk', 'vi', 'zh_CN', 'zh_TW']


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


def measure_translations(language):
    en_labels = get_language('en')
    labels = get_language(language)

    count = 0
    count_need = 0
    for en, lab in zip(en_labels.items(), labels.items()):
        count += 1
        if en[1] == lab[1]:
            count_need += 1

    count_trans = len(labels) - count_need
    return f'| {key_lang[language]} | {count_trans} | {count_trans / len(labels):.1%} |'


def measure_all_languages():
    stats = {}
    for language in languages:
        stats[key_lang[language]] = measure_translations(language)
    print('| Language | Translated species | Translated species (%) |')
    print('| -------- | ------- | ------ |')
    for _, stat in sorted(stats.items()):
        if 'English' in stat:
            continue
        print(stat)


def scrape_wikipedia(sci_name, language, failed=None):
    if failed is None:
        failed = []
    url_sci_name = sci_name.replace(" ", "_")
    url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{url_sci_name}"
    headers = {'Accept-Encoding': 'gzip', 'User-agent': 'BirdNET-Pi'}
    try:
        resp = requests.get(url=url, headers=headers, timeout=10).json()
    except Exception:
        time.sleep(1)
        try:
            resp = requests.get(url=url, headers=headers, timeout=10).json()
        except Exception as e:
            failed.append((language, sci_name, str(e)))
            return

    type = resp['type']
    if type == 'Internal error':
        return
    if type == 'disambiguation':
        failed.append((language, sci_name, type))
        return

    try:
        com_name = resp['title']
    except KeyError:
        return

    if com_name and com_name != sci_name:
        cleaned = re.sub(r'\(\S+\)', '', com_name).strip()
        if cleaned != com_name:
            print(f'*** checkme {com_name}')
        return com_name


def add_translations(language, failed=None):
    if failed is None:
        failed = []
    en_labels = get_language('en')
    labels = get_language(language)
    labels_updated = get_language(language)

    count = 0
    count_trans = 0
    count_needed = 0

    for en, lab in zip(en_labels.items(), labels.items()):
        count += 1
        if en[1] == lab[1] and ' ' in en[0]:
            count_needed += 1
            translated = scrape_wikipedia(en[0], language, failed)
            if translated and translated != en[1]:
                labels_updated[en[0]] = translated
                print(f'{lab[1]} -> {translated}')
                count_trans += 1

            time.sleep(0.1)
        if (count % 100) == 0:
            print(f'{count_trans=}', f'{count_needed=}', f'{count / len(labels):.2%}')

    print(f'{count_trans=}', f'{count_trans / len(labels):.2%}', f'{count_needed=}', f'{count_needed / len(labels):.2%}',
          f'{((count_needed - count_trans) / len(labels)):.2%}')
    print(failed)
    save_language(labels_updated, language)
    return failed

# Remove these
# ar: (طائر)
# de: (Vogel)
# fi: (lintu)
# is: (fugl)
# nl: [(vogel), (soort)]
# sv: (fågel)


def update_all_languages():
    failed = []
    for language in languages:
        print(f'start {language}')
        ret = add_translations(language)
        print(f'finished {language}')
        failed.extend(ret)
    print(failed)
