import os

from scripts.utils.helpers import MODEL_PATH, save_language


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
